function getCanonicalUrl() {
  return (
    document.querySelector("link[rel='canonical']")?.href ||
    window.location.href.split("?")[0]
  );
}

function getProfilePreview() {
  const name = document.querySelector("h1")?.textContent?.trim() || "";
  const headline =
    document.querySelector(".text-body-medium")?.textContent?.trim() ||
    document.querySelector(".pv-text-details__left-panel .text-body-medium")?.textContent?.trim() ||
    "";
  const company =
    document.querySelector(".pv-text-details__left-panel .text-body-small")?.textContent?.trim() ||
    "";
  const avatar =
    document.querySelector("img.pv-top-card-profile-picture__image") ||
    document.querySelector("img.profile-photo-edit__preview");
  const avatarUrl = avatar?.getAttribute("src") || avatar?.getAttribute("data-delayed-url") || "";
  return { name, headline, company, avatarUrl, linkedinUrl: getCanonicalUrl() };
}

function splitName(fullName) {
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 0) return { firstName: "", lastName: "" };
  if (parts.length === 1) return { firstName: parts[0], lastName: "" };
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}

async function getProfileForSave() {
  const preview = getProfilePreview();
  let avatarBase64 = "";
  let avatarContentType = "";
  if (preview.avatarUrl) {
    try {
      const response = await fetch(preview.avatarUrl);
      const blob = await response.blob();
      avatarContentType = blob.type;
      const reader = new FileReader();
      avatarBase64 = await new Promise((resolve) => {
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(blob);
      });
    } catch (error) {
      avatarBase64 = "";
      avatarContentType = "";
    }
  }
  const nameParts = splitName(preview.name);
  return {
    linkedinUrl: preview.linkedinUrl,
    firstName: nameParts.firstName,
    lastName: nameParts.lastName,
    headline: preview.headline,
    company: preview.company,
    avatarBase64,
    avatarContentType,
  };
}

function extractThreadId() {
  const match = window.location.pathname.match(/messaging\/thread\/([^/]+)/);
  return match ? match[1] : null;
}

function getMessagePreview() {
  const title =
    document.querySelector(".msg-thread__participant-name")?.textContent?.trim() ||
    document.querySelector(".msg-thread__name")?.textContent?.trim() ||
    "LinkedIn Conversation";
  const messages = collectMessages();
  const preview = messages.length ? messages[messages.length - 1].content : "";
  return { title, preview, messages, externalThreadId: extractThreadId(), linkedinUrl: findParticipantLink() };
}

function findParticipantLink() {
  const profileLink =
    document.querySelector("a.msg-thread__participant-name")?.getAttribute("href") ||
    document.querySelector("a.msg-thread__link")?.getAttribute("href") ||
    "";
  if (!profileLink) return "";
  if (profileLink.startsWith("http")) {
    return profileLink.split("?")[0];
  }
  return `${window.location.origin}${profileLink.split("?")[0]}`;
}

function collectMessages() {
  const bubbles = document.querySelectorAll(
    ".msg-s-event-listitem__message-bubble, .msg-s-message-group__messages, .msg-s-event-listitem__body"
  );
  const results = [];
  bubbles.forEach((bubble) => {
    const text = bubble.textContent?.trim() || "";
    if (!text) return;
    const isOutbound = Boolean(
      bubble.closest(".msg-s-message-group--self") ||
        bubble.closest(".msg-s-event-listitem--self")
    );
  const timestamp =
      bubble.querySelector("time")?.getAttribute("datetime") || null;
    results.push({
      direction: isOutbound ? "outbound" : "inbound",
      message_at: timestamp || null,
      content: text,
    });
  });
  return results;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "getProfilePreview") {
    sendResponse(getProfilePreview());
    return true;
  }
  if (message.type === "getProfileForSave") {
    getProfileForSave().then(sendResponse);
    return true;
  }
  if (message.type === "getMessagePreview") {
    const data = getMessagePreview();
    sendResponse({ title: data.title, preview: data.preview });
    return true;
  }
  if (message.type === "getMessagesForSave") {
    const data = getMessagePreview();
    sendResponse({
      messages: data.messages,
      externalThreadId: data.externalThreadId,
      linkedinUrl: data.linkedinUrl,
    });
    return true;
  }
  return false;
});
