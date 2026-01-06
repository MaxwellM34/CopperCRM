const apiBaseUrlInput = document.getElementById("api-base-url");
const saveButton = document.getElementById("save");
const statusEl = document.getElementById("status");

const STORAGE_KEYS = {
  API_BASE_URL: "apiBaseUrl",
};

function setStatus(message) {
  statusEl.textContent = message;
}

async function loadSettings() {
  const stored = await chrome.storage.sync.get([STORAGE_KEYS.API_BASE_URL]);
  apiBaseUrlInput.value = stored.apiBaseUrl || "";
}

async function saveSettings() {
  const apiBaseUrl = apiBaseUrlInput.value.trim();
  await chrome.storage.sync.set({ [STORAGE_KEYS.API_BASE_URL]: apiBaseUrl });
  setStatus("Saved.");
}

saveButton.addEventListener("click", () => {
  void saveSettings();
});

void loadSettings();
