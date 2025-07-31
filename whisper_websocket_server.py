#!/usr/bin/env python3
from whisper_online import *

import sys
import argparse
import os
import logging
import numpy as np
import asyncio
import websockets
import json
import io
import soundfile as sf
import signal
try:
    import requests
    import urllib.parse
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()

# server options
parser.add_argument("--host", type=str, default='localhost')
parser.add_argument("--port", type=int, default=43007)
parser.add_argument("--warmup-file", type=str, dest="warmup_file", 
        help="The path to a speech audio wav file to warm up Whisper so that the very first chunk processing is fast.")
parser.add_argument("--enable-translation", action="store_true", 
        help="Enable translation capabilities using Google Translate")

# options from whisper_online
add_shared_args(parser)
args = parser.parse_args()

set_logging(args,logger,other="")

# setting whisper object by args 
SAMPLING_RATE = 16000

size = args.model
language = args.lan
asr, online = asr_factory(args)
min_chunk = args.min_chunk_size

# Simple Google Translate API implementation
class SimpleTranslator:
    def __init__(self):
        self.base_url = "https://translate.googleapis.com/translate_a/single"
        
    def translate(self, text, src='auto', dest='en'):
        """Simple translation using Google Translate API"""
        try:
            params = {
                'client': 'gtx',
                'sl': src,
                'tl': dest,
                'dt': 't',
                'q': text
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0 and len(result[0]) > 0:
                    return result[0][0][0]
            return None
        except Exception as e:
            logger.error(f"Translation request failed: {e}")
            return None

# Initialize translator if enabled
translator = None
if args.enable_translation:
    if TRANSLATION_AVAILABLE:
        try:
            translator = SimpleTranslator()
            logger.info("Translation service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize translation service: {e}")
            translator = None
    else:
        logger.error("requests library not available. Install with: pip install requests")
        translator = None

# Language mapping for Whisper and Google Translate
WHISPER_LANGUAGES = {
    'auto': 'auto',
    'en': 'en', 'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it', 'pt': 'pt',
    'ja': 'ja', 'ko': 'ko', 'zh': 'zh', 'ar': 'ar', 'ru': 'ru', 'hi': 'hi',
    'nl': 'nl', 'pl': 'pl', 'tr': 'tr', 'sv': 'sv', 'da': 'da', 'no': 'no',
    'fi': 'fi', 'cs': 'cs', 'sk': 'sk', 'hu': 'hu', 'ro': 'ro', 'bg': 'bg',
    'hr': 'hr', 'sl': 'sl', 'et': 'et', 'lv': 'lv', 'lt': 'lt', 'uk': 'uk'
}

# warm up the ASR
msg = "Whisper is not warmed up. The first chunk processing may take longer."
if args.warmup_file:
    if os.path.isfile(args.warmup_file):
        a = load_audio_chunk(args.warmup_file,0,1)
        asr.transcribe(a)
        logger.info("Whisper is warmed up.")
    else:
        logger.critical("The warm up file is not available. "+msg)
        sys.exit(1)
else:
    logger.warning(msg)

class WhisperWebSocketProcessor:
    def __init__(self, min_chunk, enable_translation=False):
        self.min_chunk = min_chunk
        self.enable_translation = enable_translation
        self.last_end = None
        self.audio_buffer = []
        self.buffer_size = 0
        self.min_buffer_size = int(min_chunk * SAMPLING_RATE * 2)  # 2 bytes per sample (int16)
        
        # Language settings
        self.source_language = 'en'
        self.target_language = 'fr'
        
        # Create initial ASR processor
        self.create_asr_processor()

    def create_asr_processor(self):
        """Create or recreate ASR processor with current language settings"""
        # Create new args object with current settings
        current_args = argparse.Namespace(**vars(args))
        current_args.lan = self.source_language
        
        # Create new ASR and online processor
        self.asr, self.online_asr_proc = asr_factory(current_args)
        logger.info(f"Created ASR processor for language: {self.source_language}")

    def update_languages(self, source_lang, target_lang):
        """Update source and target languages"""
        old_source = self.source_language
        old_target = self.target_language
        self.source_language = source_lang
        self.target_language = target_lang
        
        # If source language changed, recreate ASR processor but don't restart transcription
        if old_source != source_lang:
            self.create_asr_processor()
            logger.info(f"Language changed from {old_source} to {source_lang}, recreated ASR processor")
            return 'source_changed'  # Indicates source language changed
        elif old_target != target_lang:
            logger.info(f"Target language changed from {old_target} to {target_lang}")
            return 'target_changed'  # Indicates only target language changed
        return 'no_change'

    def add_audio_chunk(self, audio_bytes):
        """Add raw audio bytes to buffer"""
        self.audio_buffer.append(audio_bytes)
        self.buffer_size += len(audio_bytes)

    def process_audio(self):
        """Process accumulated audio if we have enough"""
        if self.buffer_size < self.min_buffer_size:
            return None
            
        # Combine all audio chunks
        combined_audio = b''.join(self.audio_buffer)
        self.audio_buffer = []
        self.buffer_size = 0
        
        try:
            # Convert bytes to audio array
            audio_int16 = np.frombuffer(combined_audio, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Process with whisper
            self.online_asr_proc.insert_audio_chunk(audio_float32)
            result = self.online_asr_proc.process_iter()
            
            logger.debug(f"Raw whisper result: {result}")
            formatted = self.format_result(result)
            logger.debug(f"Formatted result: {formatted}")
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return None

    def format_result(self, o):
        """Format whisper output"""
        # o is a tuple: (start_time, end_time, text)
        if len(o) >= 3 and o[2] and o[2].strip():
            text = o[2].strip()
            
            if o[0] is not None and o[1] is not None:
                # Final result with timestamps
                beg, end = o[0]*1000, o[1]*1000
                if self.last_end is not None:
                    beg = max(beg, self.last_end)
                self.last_end = end
                
                return {
                    'type': 'transcription',
                    'text': text,
                    'start': beg,
                    'end': end,
                    'isFinal': True
                }
            else:
                # Incomplete result - still send it
                return {
                    'type': 'transcription',
                    'text': text,
                    'start': 0,
                    'end': 0,
                    'isFinal': False
                }
        return None

    def translate_text(self, text):
        """Translate text if translation is enabled"""
        if not self.enable_translation or not translator:
            return None
            
        try:
            # Skip translation if source and target are the same
            if self.source_language == self.target_language:
                return text
                
            # Handle auto-detect source language
            src_lang = 'auto' if self.source_language == 'auto' else self.source_language
            
            # Translate using simple API
            result = translator.translate(text, src=src_lang, dest=self.target_language)
            return result
                
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return None

    def finish(self):
        """Get final result"""
        result = self.online_asr_proc.finish()
        return self.format_result(result)

    def reset(self):
        """Reset processor state for new recording session"""
        self.online_asr_proc.init()
        self.last_end = None
        self.audio_buffer = []
        self.buffer_size = 0

async def handle_client(websocket):
    logger.info(f"Client connected from {websocket.remote_address}")
    
    # Create new processor for this client
    processor = WhisperWebSocketProcessor(args.min_chunk_size, args.enable_translation)
    processor.reset()
    
    try:
        await websocket.send(json.dumps({
            'type': 'status',
            'message': f'Connected to Whisper server (Translation: {"Enabled" if args.enable_translation else "Disabled"})'
        }))
        
        async for message in websocket:
            try:
                if isinstance(message, bytes):
                    # Raw audio data
                    processor.add_audio_chunk(message)
                    result = processor.process_audio()
                    
                    if result:
                        logger.info(f"Sending transcription: {result}")
                        await websocket.send(json.dumps(result))
                        
                        # Send translation if enabled and result is final
                        if args.enable_translation and result.get('isFinal') and result.get('text'):
                            translation = processor.translate_text(result['text'])
                            if translation:
                                translation_result = {
                                    'type': 'translation',
                                    'text': translation,
                                    'start': result.get('start', 0),
                                    'end': result.get('end', 0),
                                    'isFinal': True,
                                    'sourceLanguage': processor.source_language,
                                    'targetLanguage': processor.target_language
                                }
                                logger.info(f"Sending translation: {translation_result}")
                                await websocket.send(json.dumps(translation_result))
                    else:
                        logger.debug("No result to send")
                        
                else:
                    # JSON message
                    data = json.loads(message)
                    
                    if data.get('type') == 'start':
                        processor.reset()
                        await websocket.send(json.dumps({
                            'type': 'status',
                            'message': f'Started transcription (Source: {processor.source_language}, Target: {processor.target_language})'
                        }))
                    
                    elif data.get('type') == 'stop':
                        result = processor.finish()
                        if result:
                            await websocket.send(json.dumps(result))
                            
                            # Send final translation if enabled
                            if args.enable_translation and result.get('text'):
                                translation = processor.translate_text(result['text'])
                                if translation:
                                    translation_result = {
                                        'type': 'translation',
                                        'text': translation,
                                        'start': result.get('start', 0),
                                        'end': result.get('end', 0),
                                        'isFinal': True,
                                        'sourceLanguage': processor.source_language,
                                        'targetLanguage': processor.target_language
                                    }
                                    await websocket.send(json.dumps(translation_result))
                                    
                        await websocket.send(json.dumps({
                            'type': 'status',
                            'message': 'Stopped transcription'
                        }))
                    
                    elif data.get('type') == 'setLanguages':
                        source_lang = data.get('sourceLanguage', 'en')
                        target_lang = data.get('targetLanguage', 'fr')
                        
                        # Validate languages
                        if source_lang not in WHISPER_LANGUAGES:
                            await websocket.send(json.dumps({
                                'type': 'error',
                                'message': f'Unsupported source language: {source_lang}'
                            }))
                            continue
                            
                        change_type = processor.update_languages(source_lang, target_lang)
                        
                        if change_type == 'source_changed':
                            await websocket.send(json.dumps({
                                'type': 'languageChangeRestart',
                                'message': f'Source language changed to {source_lang}. New audio will use updated settings.',
                                'sourceLanguage': source_lang,
                                'targetLanguage': target_lang
                            }))
                        elif change_type == 'target_changed':
                            await websocket.send(json.dumps({
                                'type': 'targetLanguageChanged',
                                'message': f'Translation language changed to {target_lang}',
                                'targetLanguage': target_lang
                            }))
                        else:
                            await websocket.send(json.dumps({
                                'type': 'status',
                                'message': f'Languages updated: {source_lang} → {target_lang}'
                            }))
                        
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON'
                }))
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error handling client: {e}")

async def main():
    logger.info(f'Starting WebSocket server on {args.host}:{args.port}')
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        raise KeyboardInterrupt()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async with websockets.serve(handle_client, args.host, args.port):
        logger.info(f'WebSocket server listening on ws://{args.host}:{args.port}')
        try:
            await asyncio.Future()  # run forever
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
        sys.exit(0)