#!/usr/bin/env python3
"""
Enhanced Whisper Streaming Server Launcher
Provides easy configuration options for the Whisper WebSocket server
"""

import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(
        description="Start Whisper Streaming Server with enhanced features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic transcription only
  python start_whisper.py

  # With translation enabled
  python start_whisper.py --translate

  # Custom model and settings
  python start_whisper.py --model large-v3 --language auto --translate --chunk-size 0.2

  # Production setup
  python start_whisper.py --host 0.0.0.0 --port 43007 --model large-v3 --translate --vac --vad
        """
    )
    
    # Server settings
    parser.add_argument('--host', default='0.0.0.0', 
                       help='Server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=43007,
                       help='Server port (default: 43007)')
    
    # Model settings
    parser.add_argument('--model', default='large-v3',
                       choices=['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 
                               'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large-v3-turbo'],
                       help='Whisper model size (default: large-v3)')
    parser.add_argument('--language', '--lan', default='en',
                       help='Source language code or "auto" for detection (default: en)')
    parser.add_argument('--backend', default='faster-whisper',
                       choices=['faster-whisper', 'whisper_timestamped', 'openai-api', 'mlx-whisper'],
                       help='Whisper backend (default: faster-whisper)')
    
    # Audio processing
    parser.add_argument('--chunk-size', type=float, default=0.3,
                       help='Minimum audio chunk size in seconds (default: 0.3)')
    parser.add_argument('--vac', action='store_true',
                       help='Enable Voice Activity Controller (recommended)')
    parser.add_argument('--vad', action='store_true', 
                       help='Enable Voice Activity Detection')
    
    # Translation
    parser.add_argument('--translate', action='store_true',
                       help='Enable real-time translation using Google Translate')
    
    # Advanced options
    parser.add_argument('--warmup-file', 
                       help='Audio file to warm up Whisper model')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Build command
    cmd = [
        sys.executable, 'whisper_websocket_server.py',
        '--host', args.host,
        '--port', str(args.port),
        '--model', args.model,
        '--lan', args.language,
        '--backend', args.backend,
        '--min-chunk-size', str(args.chunk_size),
        '--log-level', args.log_level
    ]
    
    if args.vac:
        cmd.append('--vac')
    if args.vad:
        cmd.append('--vad')
    if args.translate:
        cmd.append('--enable-translation')
    if args.warmup_file:
        cmd.extend(['--warmup-file', args.warmup_file])
    
    # Print configuration
    print("🎤 Starting Whisper Streaming Server")
    print("=" * 50)
    print(f"Server: {args.host}:{args.port}")
    print(f"Model: {args.model} ({args.backend})")
    print(f"Language: {args.language}")
    print(f"Chunk Size: {args.chunk_size}s")
    print(f"Voice Activity Controller: {'✓' if args.vac else '✗'}")
    print(f"Voice Activity Detection: {'✓' if args.vad else '✗'}")
    print(f"Translation: {'✓ Enabled' if args.translate else '✗ Disabled'}")
    print("=" * 50)
    print(f"Web Interface: http://{args.host}:{args.port}")
    print(f"WebSocket URL: ws://{args.host}:{args.port}")
    print("=" * 50)
    
    # Check dependencies
    try:
        import librosa, soundfile, websockets
        if args.backend == 'faster-whisper':
            import faster_whisper
        if args.translate:
            import requests
        if args.vac or args.vad:
            import torch
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install -r requirements.txt")
        sys.exit(1)
    
    # Run server
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed with exit code {e.returncode}")
        sys.exit(e.returncode)

if __name__ == '__main__':
    main()