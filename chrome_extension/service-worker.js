// Handle side panel and popup messages
chrome.runtime.onMessage.addListener(async (message) => {
  if (message.type === 'start-translation-from-popup' || message.type === 'start-translation-from-sidepanel') {
    await startTranslation(message.tabId, message.languages);
  } else if (message.type === 'stop-translation-from-popup' || message.type === 'stop-translation-from-sidepanel') {
    await stopTranslation();
  } else if (message.type === 'open-side-panel') {
    try {
      await chrome.sidePanel.open({ windowId: message.windowId });
    } catch (error) {
      console.error('Error opening side panel:', error);
    }
  }
});

// Auto-open side panel when extension icon is clicked
chrome.action.onClicked.addListener(async (tab) => {
  try {
    console.log('🖱️ Extension icon clicked, opening side panel...');
    // Open the side panel
    await chrome.sidePanel.open({ windowId: tab.windowId });
    console.log('✅ Side panel opened successfully');
  } catch (error) {
    console.error('❌ Error opening side panel:', error);
    // If side panel fails, we could show a notification or try alternative approach
    chrome.notifications?.create({
      type: 'basic',
      iconUrl: 'icons/not-recording.png',
      title: 'Tab Audio Translator',
      message: 'Could not open side panel. Please try again.'
    });
  }
});

// Add context menu for backup access
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'open-translator',
    title: 'Open Audio Translator',
    contexts: ['action']
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'open-translator') {
    try {
      await chrome.sidePanel.open({ windowId: tab.windowId });
    } catch (error) {
      console.error('Error opening side panel from context menu:', error);
    }
  }
});

async function startTranslation(tabId, languages) {
  console.log('🌐 Starting translation for tab:', tabId);
  console.log('🔧 With languages:', languages);
  
  const existingContexts = await chrome.runtime.getContexts({});
  let translating = false;

  const offscreenDocument = existingContexts.find(
    (c) => c.contextType === 'OFFSCREEN_DOCUMENT'
  );

  // If an offscreen document is not already open, create one.
  if (!offscreenDocument) {
    console.log('📄 Creating offscreen document...');
    // Create an offscreen document.
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA'],
      justification: 'Recording from chrome.tabCapture API'
    });
  } else {
    translating = offscreenDocument.documentUrl.endsWith('#translating');
  }

  if (translating) {
    console.log('⚠️ Translation already in progress');
    return;
  }

  // Get a MediaStream for the active tab.
  console.log('🎵 Getting media stream for tab:', tabId);
  const streamId = await chrome.tabCapture.getMediaStreamId({
    targetTabId: tabId
  });

  // Send the stream ID and languages to the offscreen document to start translation.
  console.log('📤 Sending start translation message to offscreen document');
  chrome.runtime.sendMessage({
    type: 'start-translation',
    target: 'offscreen',
    data: streamId,
    languages: languages
  });

  chrome.action.setIcon({ path: '/icons/recording.png' });
}

async function stopTranslation() {
  console.log('⏹️ Stopping translation...');
  
  chrome.runtime.sendMessage({
    type: 'stop-translation',
    target: 'offscreen'
  });
  
  chrome.action.setIcon({ path: 'icons/not-recording.png' });
}