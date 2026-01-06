const statusEl = document.getElementById("status");
const authSection = document.getElementById("auth");
const authMessage = document.getElementById("auth-message");
const signInButton = document.getElementById("sign-in");
const refreshButton = document.getElementById("refresh");
const profileCard = document.getElementById("profile-card");
const messagesCard = document.getElementById("messages-card");
const emptyCard = document.getElementById("empty-card");
const addToCopperButton = document.getElementById("add-to-copper");
const saveConversationButton = document.getElementById("save-conversation");

const profileName = document.getElementById("profile-name");
const profileHeadline = document.getElementById("profile-headline");
const profileCompany = document.getElementById("profile-company");
const profileAvatar = document.getElementById("profile-avatar");
const conversationTitle = document.getElementById("conversation-title");
const conversationPreview = document.getElementById("conversation-preview");

const STORAGE_KEYS = {
  API_BASE_URL: "apiBaseUrl",
  GOOGLE_CLIENT_ID: "googleClientId",
  ID_TOKEN: "googleIdToken",
  ID_TOKEN_EXP: "googleIdTokenExp",
};

function setStatus(message, tone = "info") {
  statusEl.textContent = message;
  statusEl.dataset.tone = tone;
}

async function getSettings() {
  return chrome.storage.sync.get([STORAGE_KEYS.API_BASE_URL, STORAGE_KEYS.GOOGLE_CLIENT_ID]);
}

async function getStoredToken() {
  return chrome.storage.local.get([STORAGE_KEYS.ID_TOKEN, STORAGE_KEYS.ID_TOKEN_EXP]);
}

function decodeJwt(token) {
  const payload = token.split(".")[1];
  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
  const decoded = atob(normalized);
  return JSON.parse(decoded);
}

async function storeToken(token) {
  const payload = decodeJwt(token);
  const exp = payload.exp ? Number(payload.exp) * 1000 : 0;
  await chrome.storage.local.set({
    [STORAGE_KEYS.ID_TOKEN]: token,
    [STORAGE_KEYS.ID_TOKEN_EXP]: exp,
  });
  return exp;
}

async function fetchIdToken(interactive) {
  const settings = await getSettings();
  if (!settings.googleClientId) {
    throw new Error("Missing Google client ID. Set it in extension settings.");
  }
  const redirectUrl = chrome.identity.getRedirectURL("copper");
  const nonce = crypto.randomUUID();
  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", settings.googleClientId);
  authUrl.searchParams.set("response_type", "id_token");
  authUrl.searchParams.set("redirect_uri", redirectUrl);
  authUrl.searchParams.set("scope", "openid email profile");
  authUrl.searchParams.set("nonce", nonce);
  authUrl.searchParams.set("prompt", "select_account");

  const responseUrl = await chrome.identity.launchWebAuthFlow({
    url: authUrl.toString(),
    interactive,
  });

  if (!responseUrl) {
    throw new Error("Auth flow cancelled.");
  }
  const fragment = new URL(responseUrl).hash.substring(1);
  const params = new URLSearchParams(fragment);
  const token = params.get("id_token");
  if (!token) {
    throw new Error("No ID token returned.");
  }
  await storeToken(token);
  return token;
}

async function ensureToken() {
  const stored = await getStoredToken();
  if (stored.googleIdToken && stored.googleIdTokenExp) {
    const remaining = stored.googleIdTokenExp - Date.now();
    if (remaining > 60_000) {
      return stored.googleIdToken;
    }
  }
  return fetchIdToken(false);
}

async function promptSignIn() {
  try {
    await fetchIdToken(true);
    setStatus("Signed in.");
    await updateAuthUI();
    await refreshView();
  } catch (error) {
    setStatus(error.message || "Sign-in failed.", "error");
  }
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function classifyPage(url) {
  if (!url) return "OTHER";
  const parsed = new URL(url);
  if (parsed.hostname.includes("linkedin.com")) {
    if (parsed.pathname.startsWith("/in/")) {
      return "PROFILE";
    }
    if (parsed.pathname.startsWith("/messaging")) {
      return "MESSAGES";
    }
  }
  return "OTHER";
}

function resetCards() {
  profileCard.classList.add("hidden");
  messagesCard.classList.add("hidden");
  emptyCard.classList.add("hidden");
}

async function requestContentData(tabId, type) {
  return chrome.tabs.sendMessage(tabId, { type });
}

async function refreshView() {
  resetCards();
  setStatus("");
  await updateAuthUI();
  const tab = await getActiveTab();
  if (!tab || !tab.url) {
    emptyCard.classList.remove("hidden");
    return;
  }

  const pageType = classifyPage(tab.url);
  if (pageType === "PROFILE") {
    try {
      const data = await requestContentData(tab.id, "getProfilePreview");
      renderProfile(data);
    } catch (error) {
      emptyCard.classList.remove("hidden");
    }
  } else if (pageType === "MESSAGES") {
    try {
      const data = await requestContentData(tab.id, "getMessagePreview");
      renderMessages(data);
    } catch (error) {
      emptyCard.classList.remove("hidden");
    }
  } else {
    emptyCard.classList.remove("hidden");
  }
}

async function updateAuthUI() {
  const stored = await getStoredToken();
  const hasToken = stored.googleIdToken && stored.googleIdTokenExp > Date.now();
  if (hasToken) {
    authMessage.textContent = "Signed in.";
    signInButton.classList.add("hidden");
  } else {
    authMessage.textContent = "Sign in to enable CRM sync.";
    signInButton.classList.remove("hidden");
  }
}

function renderProfile(data) {
  if (!data) {
    emptyCard.classList.remove("hidden");
    return;
  }
  profileName.textContent = data.name || "LinkedIn Profile";
  profileHeadline.textContent = data.headline || "";
  profileCompany.textContent = data.company || "";
  if (data.avatarUrl) {
    profileAvatar.src = data.avatarUrl;
    profileAvatar.alt = data.name || "Profile avatar";
  } else {
    profileAvatar.removeAttribute("src");
    profileAvatar.alt = "";
  }
  profileCard.classList.remove("hidden");
}

function renderMessages(data) {
  if (!data) {
    emptyCard.classList.remove("hidden");
    return;
  }
  conversationTitle.textContent = data.title || "LinkedIn Conversation";
  conversationPreview.textContent = data.preview || "";
  messagesCard.classList.remove("hidden");
}

async function enrichLinkedInProfile() {
  addToCopperButton.disabled = true;
  try {
    const token = await ensureToken();
    const tab = await getActiveTab();
    const data = await requestContentData(tab.id, "getProfileForSave");
    if (!data || !data.linkedinUrl) {
      throw new Error("Could not read profile data.");
    }
    const settings = await getSettings();
    if (!settings.apiBaseUrl) {
      throw new Error("Missing API base URL. Set it in settings.");
    }
    const response = await fetch(`${settings.apiBaseUrl}/enrich/linkedin`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        linkedin_url: data.linkedinUrl,
        first_name: data.firstName,
        last_name: data.lastName,
        headline: data.headline,
        company_name: data.company,
        avatar_base64: data.avatarBase64,
        avatar_content_type: data.avatarContentType,
      }),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`API error: ${detail}`);
    }
    setStatus("Lead saved to CRM.");
  } catch (error) {
    setStatus(error.message || "Failed to save lead.", "error");
  } finally {
    addToCopperButton.disabled = false;
  }
}

async function saveConversation() {
  saveConversationButton.disabled = true;
  try {
    const token = await ensureToken();
    const tab = await getActiveTab();
    const data = await requestContentData(tab.id, "getMessagesForSave");
    if (!data || !data.messages?.length) {
      throw new Error("No messages found in the current view.");
    }
    const settings = await getSettings();
    if (!settings.apiBaseUrl) {
      throw new Error("Missing API base URL. Set it in settings.");
    }
    const payload = {
      lead_id: null,
      linkedin_url: data.linkedinUrl,
      source: "linkedin",
      external_thread_id: data.externalThreadId,
      messages: data.messages,
    };
    const response = await fetch(`${settings.apiBaseUrl}/threads/upsert`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`API error: ${detail}`);
    }
    setStatus("Conversation saved.");
  } catch (error) {
    setStatus(error.message || "Failed to save conversation.", "error");
  } finally {
    saveConversationButton.disabled = false;
  }
}

signInButton?.addEventListener("click", promptSignIn);
refreshButton?.addEventListener("click", refreshView);
addToCopperButton?.addEventListener("click", enrichLinkedInProfile);
saveConversationButton?.addEventListener("click", saveConversation);

refreshView();
