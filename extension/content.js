function getCanonicalUrl() {
  return (
    document.querySelector("link[rel='canonical']")?.href ||
    window.location.href.split("?")[0]
  );
}

function getProfilePreview() {
  const name = document.querySelector("h1")?.textContent?.trim() || "";
  const avatar =
    document.querySelector("img.pv-top-card-profile-picture__image") ||
    document.querySelector("img.pv-top-card-profile-picture__image--show") ||
    document.querySelector(".pv-top-card__photo img") ||
    document.querySelector("img.profile-photo-edit__preview") ||
    Array.from(document.querySelectorAll("img[alt]")).find(
      (img) => img.getAttribute("alt")?.trim() === name
    );
  const delayedUrl = avatar?.getAttribute("data-delayed-url") || "";
  const srcUrl = avatar?.getAttribute("src") || "";
  const avatarUrl = delayedUrl || srcUrl;
  return { name, avatarUrl, linkedinUrl: getCanonicalUrl() };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "getProfilePreview") {
    sendResponse(getProfilePreview());
    return true;
  }
  return false;
});
