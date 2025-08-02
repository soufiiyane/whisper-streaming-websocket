document.addEventListener('DOMContentLoaded', function() {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const clearBtn = document.getElementById('clearBtn');
    const status = document.getElementById('status');
    const transcriptionEl = document.getElementById('transcription');
    const translationEl = document.getElementById('translation');
    const sourceLanguageSelect = document.getElementById('sourceLanguageSelect');
    const targetLanguageSelect = document.getElementById('targetLanguageSelect');
    const originalLabel = document.getElementById('originalLabel');
    const translationLabel = document.getElementById('translationLabel');
    let isRecording = false;
    let accumulatedTranscription = '';
    let accumulatedTranslation = '';
    let currentPartialTranscription = '';
    let currentPartialTranslation = '';
    
    // Check current recording status when popup opens
    checkRecordingStatus();
    
    // Initialize language settings
    updateLanguageLabels();
    
    // Side panel is already open by default, no pin functionality needed
    
    // Language change handlers
    const updateLanguages = () => {
        const sourceLanguage = sourceLanguageSelect.value;
        const targetLanguage = targetLanguageSelect.value;
        
        // Prevent same language for source and target
        if (sourceLanguage === targetLanguage) {
            status.textContent = '⚠️ Source and target languages cannot be the same!';
            status.className = 'status connecting';
            return;
        }
        
        // Send language update to offscreen document
        chrome.runtime.sendMessage({
            type: 'update-languages',
            sourceLanguage: sourceLanguage,
            targetLanguage: targetLanguage
        });
        
        // Update UI labels
        updateLanguageLabels();
        
        // Show feedback when recording is active
        if (isRecording) {
            status.textContent = '🔄 Language settings updated during recording!';
            status.className = 'status recording';
            document.body.classList.add('recording');
        }
    };
    
    sourceLanguageSelect.addEventListener('change', updateLanguages);
    targetLanguageSelect.addEventListener('change', updateLanguages);
    
    function updateLanguageLabels() {
        const languageNames = {
            'en': 'English',
            'es': 'Spanish', 
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'ru': 'Russian',
            'hi': 'Hindi'
        };
        
        const sourceLanguage = sourceLanguageSelect.value;
        const targetLanguage = targetLanguageSelect.value;
        
        originalLabel.textContent = `🎤 Original (${languageNames[sourceLanguage] || sourceLanguage})`;
        translationLabel.textContent = `🌍 Translation (${languageNames[targetLanguage] || targetLanguage})`;
    }
    
    startBtn.addEventListener('click', async () => {
        try {
            // Get the current active tab
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            // Get current language settings
            const sourceLanguage = sourceLanguageSelect.value;
            const targetLanguage = targetLanguageSelect.value;
            
            // Validate languages
            if (sourceLanguage === targetLanguage) {
                status.textContent = '⚠️ Source and target languages cannot be the same!';
                status.className = 'status connecting';
                return;
            }
            
            // Send message to service worker to start translation with languages
            await chrome.runtime.sendMessage({
                type: 'start-translation-from-sidepanel',
                tabId: tab.id,
                languages: {
                    sourceLanguage: sourceLanguage,
                    targetLanguage: targetLanguage
                }
            });
            
            updateUI('connecting');
        } catch (error) {
            console.error('Error starting translation:', error);
            status.textContent = 'Error starting translation';
            status.className = 'status not-recording';
        }
    });
    
    stopBtn.addEventListener('click', async () => {
        try {
            // Send message to service worker to stop translation
            await chrome.runtime.sendMessage({
                type: 'stop-translation-from-sidepanel'
            });
            
            updateUI('stopped');
        } catch (error) {
            console.error('Error stopping translation:', error);
            status.textContent = 'Error stopping translation';
            status.className = 'status not-recording';
        }
    });
    
    clearBtn.addEventListener('click', () => {
        // Clear all accumulated text
        accumulatedTranscription = '';
        accumulatedTranslation = '';
        currentPartialTranscription = '';
        currentPartialTranslation = '';
        
        // Reset display
        transcriptionEl.innerHTML = 'Waiting for audio...';
        translationEl.innerHTML = 'Waiting for translation...';
        
        console.log('📝 Text cleared by user');
    });
    
    function updateUI(state) {
        switch(state) {
            case 'connecting':
                status.textContent = '🔄 Connecting to server...';
                status.className = 'status connecting';
                startBtn.disabled = true;
                stopBtn.disabled = false;
                isRecording = false;
                document.body.classList.remove('recording');
                // Clear partial text when starting new session
                currentPartialTranscription = '';
                currentPartialTranslation = '';
                break;
            case 'recording':
                status.textContent = '🔴 Translating live audio...';
                status.className = 'status recording';
                startBtn.disabled = true;
                stopBtn.disabled = false;
                isRecording = true;
                document.body.classList.add('recording');
                break;
            case 'stopped':
                status.textContent = 'Ready to translate';
                status.className = 'status not-recording';
                startBtn.disabled = false;
                stopBtn.disabled = true;
                // Don't clear the accumulated text - keep it for user to read
                // transcriptionEl.textContent = 'Waiting for audio...';
                // translationEl.textContent = 'Waiting for translation...';
                isRecording = false;
                document.body.classList.remove('recording');
                break;
            default:
                status.textContent = 'Ready to translate';
                status.className = 'status not-recording';
                startBtn.disabled = false;
                stopBtn.disabled = true;
                isRecording = false;
                document.body.classList.remove('recording');
        }
    }
    
    async function checkRecordingStatus() {
        try {
            const existingContexts = await chrome.runtime.getContexts({});
            const offscreenDocument = existingContexts.find(
                (c) => c.contextType === 'OFFSCREEN_DOCUMENT'
            );
            
            if (offscreenDocument && offscreenDocument.documentUrl.endsWith('#translating')) {
                updateUI('recording');
            } else {
                updateUI('stopped');
            }
        } catch (error) {
            console.error('Error checking recording status:', error);
            updateUI('stopped');
        }
    }
    
    // Listen for updates from offscreen document
    chrome.runtime.onMessage.addListener((message) => {
        console.log('Popup received message:', message);
        
        switch(message.type) {
            case 'translation-status-update':
                updateUI(message.status);
                break;
            case 'server-connected':
                if (status.textContent.includes('Connecting')) {
                    status.textContent = '✅ Connected! Starting audio capture...';
                    status.className = 'status connecting';
                }
                break;
            case 'transcription-started':
                updateUI('recording');
                break;
            case 'transcription-update':
                if (message.isFinal) {
                    // Add final transcription to accumulated text
                    if (message.text.trim()) {
                        accumulatedTranscription += (accumulatedTranscription ? ' ' : '') + message.text.trim();
                        currentPartialTranscription = '';
                    }
                } else {
                    // Update partial transcription
                    currentPartialTranscription = message.text;
                }
                
                // Display accumulated + current partial
                const displayText = accumulatedTranscription + 
                    (currentPartialTranscription ? (accumulatedTranscription ? ' ' : '') + 
                    `<span class="partial">${currentPartialTranscription}</span>` : '');
                
                transcriptionEl.innerHTML = displayText || 'Listening...';
                transcriptionEl.scrollTop = transcriptionEl.scrollHeight; // Auto-scroll to bottom
                break;
                
            case 'translation-update':
                if (message.isFinal) {
                    // Add final translation to accumulated text
                    if (message.text.trim()) {
                        accumulatedTranslation += (accumulatedTranslation ? ' ' : '') + message.text.trim();
                        currentPartialTranslation = '';
                    }
                } else {
                    // Update partial translation
                    currentPartialTranslation = message.text;
                }
                
                // Display accumulated + current partial
                const displayTranslation = accumulatedTranslation + 
                    (currentPartialTranslation ? (accumulatedTranslation ? ' ' : '') + 
                    `<span class="partial">${currentPartialTranslation}</span>` : '');
                
                translationEl.innerHTML = displayTranslation || 'Translation will appear here...';
                translationEl.scrollTop = translationEl.scrollHeight; // Auto-scroll to bottom
                break;
            case 'connection-error':
                status.textContent = '❌ Server connection failed - Is localhost:43007 running?';
                status.className = 'status not-recording';
                startBtn.disabled = false;
                stopBtn.disabled = true;
                isRecording = false;
                document.body.classList.remove('recording');
                break;
            case 'language-change-feedback':
                if (isRecording) {
                    status.textContent = message.message;
                    status.className = 'status recording';
                }
                break;
        }
    });
});