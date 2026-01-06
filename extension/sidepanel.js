const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const STORAGE_KEYS = {
  API_BASE_URL: "apiBaseUrl",
};

const statusEl = document.getElementById("status");

let cachedToken = null;
let cachedTokenExp = 0;

function setStatus(message) {
  statusEl.textContent = message;
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
    return;
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
    return;
  }

  const data = await response.json();
  setStatus(`Authorized: ${data.email || ""}`.trim());
}

async function init() {
  setStatus("Signing in...");
  try {
    const apiBaseUrl = await getApiBaseUrl();
    if (!apiBaseUrl) {
      throw new Error("Missing API base URL. Set it in extension options.");
    }
    const config = await fetchBackendConfig(apiBaseUrl);
    const googleClientId = config.google_client_id;
    const token = await getIdToken(googleClientId);
    await verifyWithBackend(apiBaseUrl, token);
  } catch (error) {
    setStatus(`Error: ${error?.message || "Unknown error"}`);
  }
}

init();
