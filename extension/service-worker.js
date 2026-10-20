// Configure each worker start, including a developer reload of the unpacked extension.
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {
  console.error('PathForge could not enable the toolbar side panel. Reload the extension.');
});
