const apiBaseUrlInput = document.getElementById("api-base-url");
const googleClientIdInput = document.getElementById("google-client-id");
const saveButton = document.getElementById("save-settings");
const saveStatus = document.getElementById("save-status");

const STORAGE_KEYS = {
  API_BASE_URL: "apiBaseUrl",
  GOOGLE_CLIENT_ID: "googleClientId",
};

async function loadSettings() {
  const settings = await chrome.storage.sync.get([
    STORAGE_KEYS.API_BASE_URL,
    STORAGE_KEYS.GOOGLE_CLIENT_ID,
  ]);
  apiBaseUrlInput.value = settings.apiBaseUrl || "";
  googleClientIdInput.value = settings.googleClientId || "";
}

async function saveSettings() {
  await chrome.storage.sync.set({
    [STORAGE_KEYS.API_BASE_URL]: apiBaseUrlInput.value.trim(),
    [STORAGE_KEYS.GOOGLE_CLIENT_ID]: googleClientIdInput.value.trim(),
  });
  saveStatus.textContent = "Settings saved.";
}

saveButton.addEventListener("click", saveSettings);
loadSettings();
