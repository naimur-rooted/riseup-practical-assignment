// Popup: pulls page data from the content script, then POSTs with X-API-Key.
//
// WHY chrome.storage.local AND NEVER localStorage: Manifest V3 service workers
// (and this popup's background code paths) have no window/DOM object to hang
// localStorage off of; chrome.storage.local is the supported async store that
// every extension context shares.

// WHY a constant for the URL: .env is a Python-side concept; a packed extension
// has no env, so the base URL is fixed here (change it if you move the backend).
const BACKEND_URL = "http://127.0.0.1:8017";

const els = {
  apiKey: document.getElementById("api-key"),
  saveKey: document.getElementById("save-key"),
  title: document.getElementById("title"),
  content: document.getElementById("content"),
  save: document.getElementById("save"),
  status: document.getElementById("status"),
};

function setStatus(text) {
  els.status.textContent = text;
}

async function pullPageData() {
  // WHY the popup asks: the content script cannot push to a closed popup.
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const reply = await chrome.tabs.sendMessage(tab.id, { type: "GET_SELECTION" });
  els.title.value = reply.title || "";
  // WHY fallback to the title: an empty selection would fail API validation.
  els.content.value = reply.selection || reply.title || "";
  return tab;
}

async function saveKey() {
  await chrome.storage.local.set({ apiKey: els.apiKey.value.trim() });
  setStatus("API key saved locally.");
}

async function save() {
  setStatus("Saving…");
  const tab = await pullPageData();
  const { apiKey = "" } = await chrome.storage.local.get("apiKey");
  const isKeyMissing = apiKey.length === 0;
  if (isKeyMissing) {
    setStatus("Save your API key first (top field).");
    return;
  }
  const payload = {
    title: els.title.value || tab.title,
    content: els.content.value,
    source_url: tab.url,
  };
  const response = await fetch(`${BACKEND_URL}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  setStatus(response.ok ? `Saved ✔ (mirror: ${body.mirror})` : `Failed: HTTP ${response.status}`);
}

els.saveKey.addEventListener("click", () => saveKey().catch((error) => setStatus(`Error: ${error.message}`)));
els.save.addEventListener("click", () => save().catch((error) => setStatus(`Error: ${error.message}`)));
pullPageData().catch((error) => setStatus(`Open a normal page and retry (${error.message})`));
