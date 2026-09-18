// Background service worker (Manifest V3).
//
// WHY A SERVICE WORKER AND NOT A PERSISTENT PAGE: MV3 removed persistent
// background pages. A service worker is event-driven — Chrome starts it when an
// event arrives (install, message, alarm), lets it terminate when idle, and
// restarts it on the next event. Long-lived state therefore belongs in
// chrome.storage or the backend, never in worker globals.

chrome.runtime.onInstalled.addListener((details) => {
  // WHY log only: Phase 5 keeps the worker minimal; the retry loop lives in the
  // Python backend, not here (one queue owner — much easier to reason about).
  console.log("phase9 extension installed:", details.reason);
});
