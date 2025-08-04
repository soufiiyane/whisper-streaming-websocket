let socket = null;
let audioContext = null;
let processor = null;
let mediaStream = null; // Store the media stream to properly stop it
let isTranslating = false;
let currentLanguages = { sourceLanguage: 'en', targetLanguage: 'es' }; // Store current languages

chrome.runtime.onMessage.addListener(async (message) => {
  if (message.target === 'offscreen') {
    switch (message.type) {
      case 'start-translation':
        await startTranslation(message.data, message.languages);
        break;
      case 'stop-translation':
        await stopTranslation();
        break;
      default:
        console.error('Unrecognized message:', message.type);
    }
  } else if (message.type === 'update-languages') {
    // Store the languages for later use
    currentLanguages = {
      sourceLanguage: message.sourceLanguage,
      targetLanguage: message.targetLanguage
    };
    
    // Handle language updates from popup
    if (socket && socket.readyState === WebSocket.OPEN) {
      console.log('🔄 Updating languages:', message.sourceLanguage, '->', message.targetLanguage);
      socket.send(JSON.stringify({
        type: 'setLanguages',
        sourceLanguage: message.sourceLanguage,
        targetLanguage: message.targetLanguage
      }));
      
      // Send feedback to popup
      chrome.runtime.sendMessage({
        type: 'language-change-feedback',
        message: `🔄 Languages updated: ${message.sourceLanguage} → ${message.targetLanguage}`
      });
    }
  }
});

async function connectToServer(languages) {
  return new Promise((resolve, reject) => {
    console.log('🔌 Connecting to localhost:43007...');
    
    socket = new WebSocket('ws://localhost:43007');

    socket.onopen = () => {
      console.log('✅ Connected to Whisper server');
      
      // Notify popup that we're connected
      chrome.runtime.sendMessage({
        type: 'server-connected'
      });
      
      // Use the languages passed from popup, not defaults
      const languagesToUse = languages || currentLanguages;
      console.log('🔧 Setting languages:', languagesToUse);
      
      // Send language settings to Whisper server
      socket.send(JSON.stringify({
        type: 'setLanguages',
        sourceLanguage: languagesToUse.sourceLanguage,
        targetLanguage: languagesToUse.targetLanguage
      }));
      
      // Send start message
      socket.send(JSON.stringify({ type: 'start' }));
      
      setTimeout(() => {
        resolve();
      }, 500);
    };

    socket.onclose = () => {
      console.log('❌ Disconnected from server');
      chrome.runtime.sendMessage({
        type: 'connection-error',
        error: 'Disconnected from server'
      });
    };

    socket.onerror = (error) => {
      console.error('❌ Connection error:', error);
      chrome.runtime.sendMessage({
        type: 'connection-error',
        error: error.message || 'Connection failed'
      });
      reject(error);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received message:', data);
        
        switch(data.type) {
          case 'transcription':
            console.log('📝 Transcription:', data);
            chrome.runtime.sendMessage({
              type: 'transcription-update',
              text: data.text,
              isFinal: data.isFinal
            });
            break;
            
          case 'translation':
            console.log('🌍 Translation:', data);
            chrome.runtime.sendMessage({
              type: 'translation-update',
              text: data.text,
              isFinal: data.isFinal
            });
            break;
            
          case 'status':
            console.log('📊 Status:', data.message);
            break;
            
          case 'error':
            console.error('🚨 Server error:', data.message);
            break;
            
          case 'languageChangeRestart':
            console.log('🔄 Language change restart:', data);
            chrome.runtime.sendMessage({
              type: 'language-change-feedback',
              message: data.message
            });
            break;
            
          case 'targetLanguageChanged':
            console.log('🌍 Target language changed:', data);
            chrome.runtime.sendMessage({
              type: 'language-change-feedback',
              message: data.message
            });
            break;
        }
      } catch (error) {
        console.error('Error parsing message:', error);
      }
    };
  });
}

// Convert Float32 audio to PCM16 format for Whisper server
function float32ToPCM16(float32Array) {
  const pcm16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const sample = Math.max(-1, Math.min(1, float32Array[i]));
    pcm16Array[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
  }
  return pcm16Array.buffer;
}

async function startTranslation(streamId, languages) {
  if (isTranslating) {
    console.log('⚠️ Translation already in progress');
    return;
  }

  console.log('🌐 Starting translation process...');
  console.log('📡 Stream ID:', streamId);
  console.log('🔧 Using languages:', languages);

  try {
    // Update current languages if provided
    if (languages) {
      currentLanguages = languages;
    }
    
    // Connect to server first with the correct languages
    await connectToServer(languages);
    
    chrome.runtime.sendMessage({
      type: 'translation-status-update',
      status: 'recording'
    });

    // Get media stream from tab
    mediaStream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      }
    });
    
    console.log('✅ Media stream obtained successfully');
    console.log('🎵 Media stream tracks:', mediaStream.getAudioTracks().map(track => ({
      id: track.id,
      label: track.label,
      enabled: track.enabled,
      readyState: track.readyState
    })));

    // Setup audio context for processing (16kHz for Whisper)
    audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000
    });

    const source = audioContext.createMediaStreamSource(mediaStream);
    
    // Continue to play the captured audio to the user
    source.connect(audioContext.destination);
    
    // Create processor for real-time audio processing
    processor = audioContext.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (e) => {
      if (isTranslating && socket && socket.readyState === WebSocket.OPEN) {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcmData = float32ToPCM16(inputData);
        socket.send(pcmData);
      }
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
    
    console.log('🔊 Audio processing setup complete');

    isTranslating = true;
    console.log('🚀 Real-time translation started');
    
    // Notify popup that transcription has started
    chrome.runtime.sendMessage({
      type: 'transcription-started'
    });

    // Update URL hash to indicate translation state
    window.location.hash = 'translating';
    console.log('🔗 URL hash updated to indicate translation state');

  } catch (error) {
    console.error('❌ Error starting translation:', error);
    
    // Clean up on error
    await stopTranslation();
    
    chrome.runtime.sendMessage({
      type: 'connection-error',
      error: error.message
    });
  }
}

async function stopTranslation() {
  console.log('🛑 Stop translation requested');
  
  isTranslating = false;
  
  // Stop transcription on server
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'stop' }));
  }

  // CRITICAL: Stop all media stream tracks first to release tab capture
  if (mediaStream) {
    console.log('🔇 Stopping media stream tracks...');
    mediaStream.getTracks().forEach((track) => {
      console.log(`🔇 Stopping track: ${track.id} (${track.label}) - State: ${track.readyState}`);
      track.stop();
    });
    mediaStream = null;
    console.log('✅ All media tracks stopped');
  }

  // Clean up audio processing
  if (processor) {
    console.log('🔌 Disconnecting audio processor...');
    processor.disconnect();
    processor = null;
  }

  // Close audio context
  if (audioContext) {
    console.log('🔊 Closing audio context...');
    await audioContext.close();
    audioContext = null;
    console.log('✅ Audio context closed');
  }

  // Disconnect from server
  if (socket) {
    console.log('🔌 Disconnecting from server...');
    socket.close();
    socket = null;
  }
  
  // Update URL hash
  window.location.hash = '';
  console.log('🔗 URL hash cleared');
  
  // Notify popup
  chrome.runtime.sendMessage({
    type: 'translation-status-update',
    status: 'stopped'
  });
  
  console.log('✅ Translation stopped completely - tab should be released');
}

// Cleanup when page is about to unload
window.addEventListener('beforeunload', async () => {
  console.log('🧹 Page unloading - cleaning up...');
  if (isTranslating) {
    await stopTranslation();
  }
});

// Cleanup when page becomes hidden (tab switching, etc.)
document.addEventListener('visibilitychange', async () => {
  if (document.hidden && isTranslating) {
    console.log('🧹 Page hidden - cleaning up...');
    await stopTranslation();
  }
});