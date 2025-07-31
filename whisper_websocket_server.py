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

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()

# server options
parser.add_argument("--host", type=str, default='localhost')
parser.add_argument("--port", type=int, default=43007)
parser.add_argument("--warmup-file", type=str, dest="warmup_file", 
        help="The path to a speech audio wav file to warm up Whisper so that the very first chunk processing is fast.")

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
    def __init__(self, online_asr_proc, min_chunk):
        self.online_asr_proc = online_asr_proc
        self.min_chunk = min_chunk
        self.last_end = None
        self.audio_buffer = []
        self.buffer_size = 0
        self.min_buffer_size = int(min_chunk * SAMPLING_RATE * 2)  # 2 bytes per sample (int16)

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

    def finish(self):
        """Get final result"""
        result = self.online_asr_proc.finish()
        return self.format_result(result)

async def handle_client(websocket):
    logger.info(f"Client connected from {websocket.remote_address}")
    
    # Create new processor for this client
    processor = WhisperWebSocketProcessor(online, args.min_chunk_size)
    processor.online_asr_proc.init()
    
    try:
        await websocket.send(json.dumps({
            'type': 'status',
            'message': 'Connected to Whisper server'
        }))
        
        async for message in websocket:
            try:
                if isinstance(message, bytes):
                    # Raw audio data
                    processor.add_audio_chunk(message)
                    result = processor.process_audio()
                    
                    if result:
                        logger.info(f"Sending result: {result}")
                        await websocket.send(json.dumps(result))
                    else:
                        logger.debug("No result to send")
                        
                else:
                    # JSON message
                    data = json.loads(message)
                    
                    if data.get('type') == 'start':
                        processor.online_asr_proc.init()
                        await websocket.send(json.dumps({
                            'type': 'status',
                            'message': 'Started transcription'
                        }))
                    
                    elif data.get('type') == 'stop':
                        result = processor.finish()
                        if result:
                            await websocket.send(json.dumps(result))
                        await websocket.send(json.dumps({
                            'type': 'status',
                            'message': 'Stopped transcription'
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