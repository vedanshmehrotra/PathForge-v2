// Keep this call inside the click handler: Firefox requires a user gesture.
browser.action.onClicked.addListener(() => {
  browser.sidebarAction.toggle().catch(() => {
    console.error('PathForge could not open its sidebar. Reload the extension.');
  });
});
