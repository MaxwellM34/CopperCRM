async function configureSidePanel() {
  if (!chrome.sidePanel?.setPanelBehavior) { /*TODO: Check if user w/o user in db can use extension */
    return;
  }
  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
}

async function openSidePanel(tabId) {
  if (!chrome.sidePanel?.open || !tabId) {
    return;
  }
  try {
    await chrome.sidePanel.open({ tabId });
  } catch (error) {
    console.warn("[Copper] Failed to open side panel", error);
  }
}

chrome.runtime.onInstalled.addListener(() => {
  void configureSidePanel();
});

chrome.runtime.onStartup.addListener(() => {
  void configureSidePanel();
});

chrome.action.onClicked.addListener((tab) => {
  void openSidePanel(tab?.id);
});
