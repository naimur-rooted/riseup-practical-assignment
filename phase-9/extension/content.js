// Content script: extracts the page title and the user's current selection.
//
// WHY PULL, NOT PUSH: the popup is not always open, so proactively messaging it
// would fail — there is nothing listening yet. Instead the popup REQUESTS the
// data when it opens (chrome.tabs.sendMessage) and this script answers here.

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const isSelectionRequest = Boolean(message) && message.type === "GET_SELECTION";
  if (isSelectionRequest) {
    sendResponse({
      ok: true,
      title: document.title,
      selection: window.getSelection().toString(),
      source_url: window.location.href,
    });
  }
  return false; // synchronous reply; nothing async is pending
});
