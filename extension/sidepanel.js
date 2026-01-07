const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const STORAGE_KEYS = {
  API_BASE_URL: "apiBaseUrl",
};

const statusEl = document.getElementById("status");
const profileEl = document.getElementById("profile");

let cachedToken = null;
let cachedTokenExp = 0;
let cachedApiBaseUrl = null;
let cachedGoogleClientId = null;
let isAuthorized = false;

function setStatus(message) {
  statusEl.textContent = message;
}

function setProfileMessage(message) {
  profileEl.textContent = message;
}

function renderProfile(data) {
  profileEl.textContent = "";
  if (!data) return;

  const fields = [
    { label: "Name", value: data.name },
    { label: "Occupation", value: data.occupation },
    { label: "Company", value: data.company },
    { label: "Email", value: data.email },
    { label: "Location", value: data.location },
    { label: "Description", value: data.description },
  ];

  fields.forEach((field) => {
    if (!field.value) return;
    const row = document.createElement("div");
    row.className = "profile-row";
    const label = document.createElement("span");
    label.className = "profile-label";
    label.textContent = `${field.label}: `;
    const value = document.createElement("span");
    value.textContent = field.value;
    row.appendChild(label);
    row.appendChild(value);
    profileEl.appendChild(row);
  });
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
      setProfileMessage("Open a LinkedIn profile to see CRM data.");
      return;
    }

    const token = await getIdToken(cachedGoogleClientId);
    const data = await fetchProfile(cachedApiBaseUrl, token, url);
    if (!data?.found) {
      setProfileMessage("No CRM record for this profile.");
      return;
    }

    renderProfile(data);
  } catch (error) {
    setProfileMessage("Error loading CRM data.");
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
  } catch (error) {
    setStatus(`Error: ${error?.message || "Unknown error"}`);
    setProfileMessage("");
  }
}

init();

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
