# Whisper Streaming

Real-time speech-to-text transcription and translation system built on OpenAI's Whisper model with WebSocket support and optional Google Translate integration.

## Installation

### Required Dependencies
```bash
pip install librosa soundfile websockets
```

### Whisper Backend (choose one)
- **faster-whisper** (recommended): `pip install faster-whisper`
- **whisper-timestamped**: `pip install git+https://github.com/linto-ai/whisper-timestamped`
- **OpenAI API**: `pip install openai` (requires `OPENAI_API_KEY` environment variable)
- **MLX Whisper** (Apple Silicon): `pip install mlx-whisper`

### Optional Features
- **Voice Activity Detection**: `pip install torch torchaudio`
- **Translation**: `pip install requests` (for Google Translate integration)

## Usage

### Quick Start - WebSocket Server

The easiest way to get started is using the enhanced launcher:

```bash
# Basic transcription only
python start_whisper.py

# With translation enabled
python start_whisper.py --translate --vac --vad

# Production setup
python start_whisper.py --host 0.0.0.0 --port 43007 --model large-v3 --translate --vac --vad
```

Then open `index.html` in your browser or navigate to `http://localhost:43007` for the web interface.

### Command Line Options

#### start_whisper.py
```bash
python start_whisper.py --help

Options:
  --host HOST           Server host (default: 0.0.0.0)
  --port PORT           Server port (default: 43007)
  --model MODEL         Whisper model size (default: large-v3)
                        Options: tiny, base, small, medium, large-v1, large-v2, large-v3, large-v3-turbo
  --language LANG       Source language code or "auto" (default: en)
  --backend BACKEND     Whisper backend (default: faster-whisper)
                        Options: faster-whisper, whisper_timestamped, openai-api, mlx-whisper
  --chunk-size SIZE     Audio chunk size in seconds (default: 0.3)
  --vac                 Enable Voice Activity Controller (recommended)
  --vad                 Enable Voice Activity Detection
  --translate           Enable real-time translation using Google Translate
  --warmup-file FILE    Audio file to warm up Whisper model
  --log-level LEVEL     Logging level (default: INFO)
```

#### whisper_online.py (File Processing)
Process pre-recorded audio files:

```bash
python whisper_online.py demo.wav --language en --min-chunk-size 1
```

Key options:
- `--model`: Whisper model size (tiny to large-v3)
- `--language`: Source language or "auto" for detection
- `--backend`: Choose Whisper backend
- `--vac`: Voice Activity Controller (recommended)
- `--vad`: Voice Activity Detection
- `--task`: "transcribe" or "translate" (to English)

### Web Interface Features

- **Language Selection**: Choose source and target languages
- **Real-time Switching**: Change languages during recording
- **Voice Activity Indicator**: Visual feedback for speech detection
- **Dual Output**: Separate panels for transcription and translation
- **WebSocket Connection**: Real-time audio streaming

### As a Python Module

```python
from whisper_online import *

# Initialize ASR
asr = FasterWhisperASR("en", "large-v3")
asr.use_vad()  # Enable voice activity detection

# Create processor
online = OnlineASRProcessor(asr)

# Process audio chunks
while audio_available:
    audio_chunk = get_audio_chunk()  # Your audio source
    online.insert_audio_chunk(audio_chunk)
    result = online.process_iter()
    if result[2]:  # If there's text
        print(f"Transcription: {result[2]}")

# Get final result
final_result = online.finish()
```


## Project Structure

```
├── whisper_online.py           # Core streaming processor and ASR backends
├── whisper_websocket_server.py # WebSocket server with translation support
├── start_whisper.py            # Easy launcher script
├── index.html                  # Web interface for real-time transcription
├── silero_vad_iterator.py      # Voice Activity Detection implementation
└── demo.wav                    # Sample audio file for testing
```

## Features

- **Real-time Streaming**: Processes audio chunks with low latency
- **Multiple Backends**: Support for faster-whisper, whisper-timestamped, OpenAI API, and MLX
- **Voice Activity Detection**: Optimized processing with VAD/VAC
- **Translation Support**: Optional Google Translate integration
- **Web Interface**: Browser-based real-time transcription
- **Language Switching**: Change languages during recording
- **Flexible Configuration**: Extensive command-line options

## Supported Languages

All Whisper-supported languages including: English, Spanish, French, German, Italian, Portuguese, Japanese, Korean, Chinese, Arabic, Russian, Hindi, Dutch, Polish, Turkish, Swedish, Danish, Norwegian, Finnish, Czech, Slovak, Hungarian, Romanian, Bulgarian, Croatian, Slovenian, Estonian, Latvian, Lithuanian, Ukrainian, and more.

