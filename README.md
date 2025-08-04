# Whisper Streaming WebSocket

Real-time speech-to-text transcription and translation system built exclusively with **faster-whisper** for optimal performance. Features WebSocket support for live audio streaming and optional Google Translate integration.

## Installation

### Required Dependencies
```bash
pip install librosa soundfile websockets
```

### Faster-Whisper Backend
This project uses **faster-whisper** exclusively for the best balance of speed and accuracy:

```bash
pip install faster-whisper
```

**For GPU Support (Recommended):**
- Install NVIDIA libraries: CUDNN 8.5.0 and CUDA 11.7
- Navigate to `whisper_online.py` and uncomment the GPU model line (around line 119)
- GPU provides significantly faster real-time processing

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
```

**Server Configuration:**
- `--host HOST` - Server host address (default: 0.0.0.0)
  - Use `0.0.0.0` to accept connections from any IP
  - Use `localhost` for local-only access
- `--port PORT` - Server port number (default: 43007)
  - Choose any available port for the WebSocket server

**Model Settings:**
- `--model MODEL` - Whisper model size (default: large-v3)
  - Options: `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3`, `large-v3-turbo`
  - Larger models = better accuracy but slower processing
  - `large-v3` recommended for production use
- `--language LANG` - Source language code (default: en)
  - Use `auto` for automatic language detection
  - Use specific codes: `en`, `es`, `fr`, `de`, `it`, `pt`, `ja`, `ko`, `zh`, etc.

**Audio Processing:**
- `--chunk-size SIZE` - Minimum audio chunk size in seconds (default: 0.3)
  - Smaller values = lower latency but more processing overhead
  - Larger values = higher latency but more efficient processing
- `--vac` - Enable Voice Activity Controller (recommended)
  - Automatically detects speech start/end for better processing
  - Reduces unnecessary processing during silence
- `--vad` - Enable Voice Activity Detection
  - Filters out non-speech audio segments
  - Improves accuracy by focusing on actual speech

**Features:**
- `--translate` - Enable real-time translation using Google Translate
  - Requires `requests` library: `pip install requests`
  - Provides live translation alongside transcription

**Advanced Options:**
- `--warmup-file FILE` - Audio file to warm up Whisper model
  - Pre-loads model with sample audio for faster first chunk processing
  - Use any WAV file for warming up
- `--log-level LEVEL` - Logging verbosity (default: INFO)
  - Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Use `DEBUG` for troubleshooting

#### whisper_online.py (File Processing)
Process pre-recorded audio files for testing and development:

```bash
python whisper_online.py demo.wav --language en --min-chunk-size 1
```

**File Processing Options:**
- `--model MODEL` - Whisper model size (tiny to large-v3)
- `--language LANG` - Source language or "auto" for automatic detection
- `--min-chunk-size SIZE` - Minimum chunk size for processing (seconds)
- `--vac` - Enable Voice Activity Controller for better segmentation
- `--vad` - Enable Voice Activity Detection to filter non-speech
- `--task TASK` - Processing task: "transcribe" or "translate" (to English)
- `--buffer-trimming` - Buffer management strategy for long audio files

### Web Interface Features

- **Language Selection**: Choose from 25+ supported languages for source and target
- **Real-time Language Switching**: Change languages during active recording without interruption
- **Voice Activity Indicator**: Visual feedback showing when speech is detected
- **Dual Output Panels**: Separate displays for original transcription and translation
- **WebSocket Connection**: Low-latency real-time audio streaming
- **Auto-scroll**: Automatically scrolls to show latest transcription results
- **Responsive Design**: Works on desktop and mobile devices

### Chrome Extension

The included Chrome extension captures audio from any browser tab and provides real-time transcription and translation:

**Features:**
- **Tab Audio Capture**: Capture audio from YouTube, podcasts, videos, any web content
- **Side Panel Interface**: Persistent panel that stays open while browsing
- **Real-time Processing**: Live transcription and translation as audio plays
- **Language Controls**: Change source and target languages during recording
- **Text Accumulation**: Keeps all transcriptions for easy reading

**Installation:**
1. Load the extension from `chrome_extension/` folder in Chrome Developer Mode
2. Start the Whisper server: `python start_whisper.py --translate`
3. Click extension icon to open side panel
4. Navigate to any tab with audio content and start translation

### As a Python Module

```python
from whisper_online import *

# Initialize faster-whisper ASR
asr = FasterWhisperASR("en", "large-v3")
asr.use_vad()  # Enable voice activity detection

# Create online processor
online = OnlineASRProcessor(asr)

# Process audio chunks in real-time
while audio_available:
    audio_chunk = get_audio_chunk()  # Your audio source (16kHz, float32)
    online.insert_audio_chunk(audio_chunk)
    result = online.process_iter()
    
    if result[2]:  # If there's transcribed text
        start_time, end_time, text = result
        print(f"[{start_time:.2f}s - {end_time:.2f}s]: {text}")

# Get final result when done
final_result = online.finish()
if final_result[2]:
    print(f"Final: {final_result[2]}")
```


## Project Structure

```
├── whisper_online.py           # Core streaming processor with faster-whisper backend
├── whisper_websocket_server.py # WebSocket server with translation support
├── start_whisper.py            # Enhanced launcher script with all options
├── index.html                  # Web interface for real-time transcription
├── silero_vad_iterator.py      # Voice Activity Detection implementation
├── chrome_extension/           # Chrome extension for tab audio capture
│   ├── manifest.json          # Extension configuration
│   ├── sidepanel.html         # Extension UI
│   ├── sidepanel.js           # Extension logic
│   ├── service-worker.js      # Background script
│   └── offscreen.js           # Audio processing
├── frontend/                   # Documentation website
│   ├── index.html             # Project documentation
│   └── styles.css             # Documentation styling
└── demo.wav                    # Sample audio file for testing
```

## Features

- **Real-time Streaming**: Processes audio chunks with low latency using WebSocket protocol
- **Faster-Whisper Backend**: Exclusively uses faster-whisper for optimal speed and accuracy
- **Voice Activity Detection**: Smart processing with VAD/VAC to reduce computational overhead
- **Live Translation**: Optional Google Translate integration for multilingual support
- **Web Interface**: Browser-based real-time transcription with responsive design
- **Chrome Extension**: Capture and translate audio from any browser tab
- **Language Switching**: Change source and target languages during active recording
- **GPU Acceleration**: Support for NVIDIA GPU acceleration for faster processing
- **Flexible Configuration**: Extensive command-line options for customization

## Supported Languages

**Source Languages (Whisper):** All 99 Whisper-supported languages including:
- **European**: English, Spanish, French, German, Italian, Portuguese, Dutch, Polish, Turkish, Swedish, Danish, Norwegian, Finnish, Czech, Slovak, Hungarian, Romanian, Bulgarian, Croatian, Slovenian, Estonian, Latvian, Lithuanian, Ukrainian
- **Asian**: Japanese, Korean, Chinese (Mandarin), Hindi, Arabic, Russian, Thai, Vietnamese, Indonesian, Malay
- **Others**: Hebrew, Persian, Urdu, Bengali, Tamil, Telugu, Gujarati, Marathi, and many more

**Translation Languages (Google Translate):** 100+ languages supported for real-time translation

**Language Detection:** Automatic language detection available with `--language auto` option

## Performance Notes

- **GPU vs CPU**: GPU acceleration provides 4-5x faster processing than CPU-only
- **Model Size Impact**: 
  - `tiny`: Fastest, lower accuracy
  - `base/small`: Good balance for real-time use
  - `medium`: Better accuracy, moderate speed
  - `large-v3`: Best accuracy, requires more resources
- **Chunk Size**: Smaller chunks (0.1-0.3s) = lower latency, larger chunks (0.5-1.0s) = better accuracy
- **VAD Benefits**: Reduces processing by 30-50% by skipping silence periods

