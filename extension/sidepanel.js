const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const STORAGE_KEYS = {
  API_BASE_URL: "apiBaseUrl",
};

const statusEl = document.getElementById("status");
const profileMessageEl = document.getElementById("profile-message");
const profileCardEl = document.getElementById("profile-card");
const profileAvatarEl = document.getElementById("profile-avatar");
const profileNameEl = document.getElementById("profile-name");
const profileSubtitleEl = document.getElementById("profile-subtitle");
const profileDetailsEl = document.getElementById("profile-details");
const addButtonEl = document.getElementById("add-button");

let cachedToken = null;
let cachedTokenExp = 0;
let cachedApiBaseUrl = null;
let cachedGoogleClientId = null;
let isAuthorized = false;
let lastProfileUrl = "";
let pollTimerId = null;
let previewPollTimerId = null;
let lastPreviewKey = "";
let lastAutoSyncKey = "";
let currentPreview = null;
let currentLinkedinUrl = "";

function setStatus(message) {
  statusEl.textContent = message;
}

function setProfileMessage(message) {
  profileMessageEl.textContent = message || "";
  profileCardEl.style.display = message ? "none" : "block";
}

function setAddButtonVisible(visible) {
  addButtonEl.style.display = visible ? "block" : "none";
}

function setProfileHeader(name, subtitle, avatarUrl) {
  profileNameEl.textContent = name || "LinkedIn Profile";
  if (profileSubtitleEl) {
    profileSubtitleEl.textContent = subtitle || "";
    profileSubtitleEl.style.display = subtitle ? "block" : "none";
  }
  if (avatarUrl) {
    profileAvatarEl.src = avatarUrl;
    profileAvatarEl.style.visibility = "visible";
  } else {
    profileAvatarEl.removeAttribute("src");
    profileAvatarEl.style.visibility = "hidden";
  }
}

function clearDetails() {
  profileDetailsEl.textContent = "";
}

function addDetail(label, value) {
  const section = document.createElement("div");
  section.className = "detail-section";
  const labelEl = document.createElement("div");
  labelEl.className = "detail-label";
  labelEl.textContent = label;
  const valueEl = document.createElement("div");
  valueEl.className = "detail-value";
  valueEl.textContent = value;
  section.appendChild(labelEl);
  section.appendChild(valueEl);
  profileDetailsEl.appendChild(section);
}

function addLinkDetail(label, value) {
  const section = document.createElement("div");
  section.className = "detail-section";
  const labelEl = document.createElement("div");
  labelEl.className = "detail-label";
  labelEl.textContent = label;
  const valueEl = document.createElement("a");
  valueEl.className = "detail-value detail-link";
  valueEl.href = value;
  valueEl.target = "_blank";
  valueEl.rel = "noreferrer";
  valueEl.textContent = value;
  section.appendChild(labelEl);
  section.appendChild(valueEl);
  profileDetailsEl.appendChild(section);
}

function buildPreviewKey(preview) {
  if (!preview) return "";
  return [
    preview.name,
    preview.avatarUrl,
    preview.jobTitle,
    preview.company,
    preview.employmentType,
  ]
    .map((value) => value || "")
    .join("|");
}

function buildLeadPayload(preview, linkedinUrl, source, createIfMissing) {
  return {
    url: linkedinUrl,
    name: preview?.name || "",
    jobTitle: preview?.jobTitle || "",
    company: preview?.company || "",
    avatarUrl: preview?.avatarUrl || "",
    source,
    createIfMissing,
  };
}

function hasLeadPayloadData(payload) {
  return Boolean(
    payload?.name ||
      payload?.jobTitle ||
      payload?.company ||
      payload?.avatarUrl
  );
}

function renderDetails(data, linkedinUrl, preview) {
  clearDetails();
  const jobTitle = data?.occupation || preview?.jobTitle;
  const employmentType = preview?.employmentType;
  const company = data?.company || preview?.company;

  if (jobTitle) {
    addDetail("Job Title", jobTitle);
  }
  if (employmentType) {
    addDetail("Employment", employmentType);
  }
  if (linkedinUrl) {
    addLinkDetail("LinkedIn", linkedinUrl);
  }
  if (company) {
    const section = document.createElement("div");
    section.className = "detail-section";
    const labelEl = document.createElement("div");
    labelEl.className = "detail-label";
    labelEl.textContent = "Company Info";
    const valueEl = document.createElement("div");
    valueEl.className = "detail-value";
    valueEl.textContent = `Name: ${company}`;
    section.appendChild(labelEl);
    section.appendChild(valueEl);
    profileDetailsEl.appendChild(section);
  }
}

function updateProfileView(data, linkedinUrl, preview) {
  const name = data?.name || preview?.name || "";
  const company = data?.company || preview?.company || "";
  setProfileMessage("");
  setProfileHeader(name, company, preview?.avatarUrl);
  setAddButtonVisible(!data?.found);
  renderDetails(data?.found ? data : null, linkedinUrl, preview);
  lastPreviewKey = buildPreviewKey(preview);
}

async function upsertLead(apiBaseUrl, token, payload) {
  const response = await fetch(`${apiBaseUrl}/extension/lead`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data.detail || data.error || JSON.stringify(data);
    } catch (error) {
      detail = await response.text();
    }
    throw new Error(detail || "Failed to save lead");
  }

  return response.json();
}

async function maybeAutoSync(data, preview, linkedinUrl) {
  if (!data?.found || !preview || !linkedinUrl) return;
  if (!cachedApiBaseUrl || !cachedGoogleClientId) return;

  const payload = buildLeadPayload(preview, linkedinUrl, "extension:auto", false);
  if (!hasLeadPayloadData(payload)) return;

  const key = `${linkedinUrl}|${buildPreviewKey(preview)}`;
  if (!key || key === lastAutoSyncKey) return;
  lastAutoSyncKey = key;

  try {
    const token = await getIdToken(cachedGoogleClientId);
    const result = await upsertLead(cachedApiBaseUrl, token, payload);
    if (result?.found) {
      updateProfileView(result, linkedinUrl, preview);
    }
  } catch (error) {
    // Ignore auto-sync failures.
  }
}

function stopPreviewPolling() {
  if (previewPollTimerId) {
    clearInterval(previewPollTimerId);
    previewPollTimerId = null;
  }
}

function startPreviewPolling(tabId, linkedinUrl, data) {
  stopPreviewPolling();
  let attempts = 0;
  const maxAttempts = 8;
  const intervalMs = 750;
  previewPollTimerId = setInterval(async () => {
    attempts += 1;
    if (attempts > maxAttempts || lastProfileUrl !== linkedinUrl) {
      stopPreviewPolling();
      return;
    }
    const preview = await fetchProfilePreview(tabId);
    if (!preview) return;
    const key = buildPreviewKey(preview);
    if (!key || key === lastPreviewKey) return;
    currentPreview = preview;
    updateProfileView(data, linkedinUrl, preview);
    await maybeAutoSync(data, preview, linkedinUrl);
  }, intervalMs);
}

function decodeJwt(token) {
  const payload = token.split(".")[1];
  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
  const decoded = atob(normalized);
  return JSON.parse(decoded);
}

function cacheToken(token) {
  cachedToken = token;
  try {
    const payload = decodeJwt(token);
    cachedTokenExp = payload.exp ? Number(payload.exp) * 1000 : 0;
  } catch (error) {
    cachedTokenExp = 0;
  }
}

function hasValidToken() {
  return cachedToken && cachedTokenExp - Date.now() > 60_000;
}

async function getApiBaseUrl() {
  const stored = await chrome.storage.sync.get([STORAGE_KEYS.API_BASE_URL]);
  return stored.apiBaseUrl || DEFAULT_API_BASE_URL;
}

async function fetchBackendConfig(apiBaseUrl) {
  const response = await fetch(`${apiBaseUrl}/auth/config`);
  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data.detail || data.error || JSON.stringify(data);
    } catch (error) {
      detail = await response.text();
    }
    throw new Error(detail || "Failed to load backend config");
  }
  return response.json();
}

async function fetchIdToken(googleClientId) {
  if (!googleClientId) {
    throw new Error("Missing Google client ID from backend config");
  }

  const redirectUrl = chrome.identity.getRedirectURL("copper");
  const nonce = crypto.randomUUID();
  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", googleClientId);
  authUrl.searchParams.set("response_type", "id_token");
  authUrl.searchParams.set("redirect_uri", redirectUrl);
  authUrl.searchParams.set("scope", "openid email profile");
  authUrl.searchParams.set("nonce", nonce);
  authUrl.searchParams.set("prompt", "select_account");

  const responseUrl = await chrome.identity.launchWebAuthFlow({
    url: authUrl.toString(),
    interactive: true,
  });

  if (!responseUrl) {
    throw new Error("Auth flow cancelled");
  }

  const fragment = new URL(responseUrl).hash.substring(1);
  const params = new URLSearchParams(fragment);
  const token = params.get("id_token");
  if (!token) {
    throw new Error("No ID token returned");
  }

  return token;
}

async function getIdToken(googleClientId) {
  if (hasValidToken()) {
    return cachedToken;
  }
  const token = await fetchIdToken(googleClientId);
  cacheToken(token);
  return token;
}

async function verifyWithBackend(apiBaseUrl, token) {
  const response = await fetch(`${apiBaseUrl}/auth/verify`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (response.status === 403) {
    setStatus("Not authorized");
    return false;
  }

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data.detail || data.error || JSON.stringify(data);
    } catch (error) {
      detail = await response.text();
    }
    setStatus(`Error: ${detail || "Request failed"}`);
    return false;
  }

  const data = await response.json();
  setStatus(`Authorized: ${data.email || ""}`.trim());
  return true;
}

async function fetchProfilePreview(tabId) {
  if (!tabId || !chrome.tabs?.sendMessage) {
    return null;
  }
  try {
    return await chrome.tabs.sendMessage(tabId, { type: "getProfilePreview" });
  } catch (error) {
    return null;
  }
}

function isLinkedInProfileUrl(url) {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    if (!parsed.hostname.endsWith("linkedin.com")) return false;
    const path = parsed.pathname.toLowerCase();
    return path.startsWith("/in/") || path.startsWith("/pub/");
  } catch (error) {
    return false;
  }
}

async function fetchProfile(apiBaseUrl, token, linkedinUrl) {
  const response = await fetch(`${apiBaseUrl}/extension/profile`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ url: linkedinUrl }),
  });

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data.detail || data.error || JSON.stringify(data);
    } catch (error) {
      detail = await response.text();
    }
    throw new Error(detail || "Failed to load CRM data");
  }

  return response.json();
}

async function refreshProfile() {
  if (!isAuthorized) {
    setProfileMessage("");
    return;
  }
  if (!cachedApiBaseUrl || !cachedGoogleClientId) {
    setProfileMessage("");
    return;
  }
  if (!chrome.tabs?.query) {
    setProfileMessage("");
    return;
  }

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = tab?.url || "";
    if (!isLinkedInProfileUrl(url)) {
      lastProfileUrl = "";
      currentPreview = null;
      currentLinkedinUrl = "";
      setProfileMessage("Open a LinkedIn profile to see CRM data.");
      return;
    }

    const preview = await fetchProfilePreview(tab?.id);
    const linkedinUrl = url;
    lastProfileUrl = url;
    currentPreview = preview;
    currentLinkedinUrl = linkedinUrl;

    const token = await getIdToken(cachedGoogleClientId);
    const data = await fetchProfile(cachedApiBaseUrl, token, linkedinUrl);
    updateProfileView(data, linkedinUrl, preview);
    startPreviewPolling(tab?.id, linkedinUrl, data);
    await maybeAutoSync(data, preview, linkedinUrl);
  } catch (error) {
    setProfileMessage("Error loading CRM data.");
  }
}

async function pollForProfileChange() {
  if (!isAuthorized || !chrome.tabs?.query) {
    return;
  }
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = tab?.url || "";
    if (!isLinkedInProfileUrl(url)) {
      lastProfileUrl = "";
      stopPreviewPolling();
      return;
    }
    if (url !== lastProfileUrl) {
      await refreshProfile();
    }
  } catch (error) {
    // Ignore polling errors.
  }
}

async function init() {
  setStatus("Signing in...");
  try {
    const apiBaseUrl = await getApiBaseUrl();
    if (!apiBaseUrl) {
      throw new Error("Missing API base URL. Set it in extension options.");
    }
    const config = await fetchBackendConfig(apiBaseUrl);
    cachedApiBaseUrl = apiBaseUrl;
    cachedGoogleClientId = config.google_client_id;
    const token = await getIdToken(cachedGoogleClientId);
    isAuthorized = await verifyWithBackend(apiBaseUrl, token);
    await refreshProfile();
    if (!pollTimerId) {
      pollTimerId = setInterval(pollForProfileChange, 1500);
    }
  } catch (error) {
    setStatus(`Error: ${error?.message || "Unknown error"}`);
    setProfileMessage("");
  }
}

init();

if (addButtonEl) {
  addButtonEl.addEventListener("click", async () => {
    if (!currentPreview || !currentLinkedinUrl) return;
    if (!cachedApiBaseUrl || !cachedGoogleClientId) return;
    const payload = buildLeadPayload(currentPreview, currentLinkedinUrl, "extension:add", true);
    if (!hasLeadPayloadData(payload)) return;
    try {
      const token = await getIdToken(cachedGoogleClientId);
      const result = await upsertLead(cachedApiBaseUrl, token, payload);
      if (result?.found) {
        updateProfileView(result, currentLinkedinUrl, currentPreview);
        setAddButtonVisible(false);
      }
    } catch (error) {
      setProfileMessage("Error saving to CRM.");
    }
  });
}

if (chrome.tabs?.onActivated) {
  chrome.tabs.onActivated.addListener(() => {
    void refreshProfile();
  });
}

if (chrome.tabs?.onUpdated) {
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if ((changeInfo.status === "complete" || changeInfo.url) && tab?.active) {
      void refreshProfile();
    }
  });
}
