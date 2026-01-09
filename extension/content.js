function getCanonicalUrl() {
  const href = window.location.href.split("?")[0];
  const path = window.location.pathname.toLowerCase();
  if (path.startsWith("/in/") || path.startsWith("/pub/")) {
    return href;
  }
  return document.querySelector("link[rel='canonical']")?.href || href;
}

function normalizeText(value) {
  return (value || "").replace(/\s+/g, " ").trim();
}

function getTextFromElement(element) {
  if (!element) return "";
  const hidden =
    element.matches?.("span[aria-hidden='true']")
      ? element
      : element.querySelector?.("span[aria-hidden='true']");
  const text = hidden?.textContent || element.textContent || "";
  return normalizeText(text);
}

function getTextFromSelector(container, selector, excluded) {
  if (!container) return "";
  const nodes = Array.from(container.querySelectorAll(selector));
  for (const node of nodes) {
    if (excluded && excluded.contains(node)) continue;
    const text = getTextFromElement(node);
    if (text) return text;
  }
  return "";
}

function getExperienceSection() {
  const anchors = Array.from(
    document.querySelectorAll("a[data-field^='experience_']")
  );
  for (const anchor of anchors) {
    const section = anchor.closest("section");
    if (section) return section;
  }

  return null;
}

function getTopExperienceItems(section) {
  if (!section) return [];
  const items = Array.from(section.querySelectorAll("li")).filter((item) => {
    if (!item.querySelector(":scope > div[data-view-name='profile-component-entity']")) {
      return false;
    }
    return Boolean(item.querySelector("a[data-field^='experience_']"));
  });
  if (items.length) return items;
  return Array.from(section.querySelectorAll("li")).filter((item) =>
    item.querySelector(":scope > div[data-view-name='profile-component-entity']")
  );
}

function getEntityContainer(item) {
  if (!item) return null;
  return (
    item.querySelector(":scope > div[data-view-name='profile-component-entity']") || item
  );
}

function getHeaderRow(container) {
  if (!container) return null;
  return (
    container.querySelector(":scope .display-flex.flex-row.justify-space-between") ||
    container
  );
}

function getBoldText(container, excluded) {
  return getTextFromSelector(
    container,
    ".hoverable-link-text.t-bold span[aria-hidden='true'], .hoverable-link-text.t-bold span.visually-hidden, span.t-bold span[aria-hidden='true']",
    excluded
  );
}

function getCompanyLinkText(container, excluded) {
  return getTextFromSelector(
    container,
    "a[href*='/company/'] span.t-14.t-normal span[aria-hidden='true'], a[href*='/company/'] span.t-14.t-normal",
    excluded
  );
}

function getCompanyLinkUrl(container, excluded) {
  if (!container) return "";
  const anchors = Array.from(container.querySelectorAll("a[href*='/company/']"));
  for (const anchor of anchors) {
    if (excluded && excluded.contains(anchor)) continue;
    const href = anchor.getAttribute("href") || "";
    if (href) {
      return href.split("?")[0];
    }
  }
  return "";
}

function getCompanyLineText(container, excluded) {
  return getTextFromSelector(
    container,
    "span.t-14.t-normal:not(.t-black--light) span[aria-hidden='true'], span.t-14.t-normal:not(.t-black--light)",
    excluded
  );
}

function getDateLineText(container) {
  const el =
    container.querySelector("span.t-14.t-normal.t-black--light span[aria-hidden='true']") ||
    container.querySelector("span.t-14.t-normal.t-black--light");
  return getTextFromElement(el);
}

function splitCompanyAndEmployment(text) {
  const parts = text.split(/\u00b7/).map(normalizeText).filter(Boolean);
  if (!parts.length) {
    return { company: "", employmentType: "" };
  }
  const company = parts[0] || "";
  const employmentType = parts.length > 1 ? parts.slice(1).join(" | ") : "";
  return { company, employmentType };
}

function isCurrentRole(dateText) {
  return /present|current/i.test(dateText || "");
}

function findNestedRoleList(item) {
  const scopedLists = Array.from(
    item.querySelectorAll(":scope .pvs-entity__sub-components > ul")
  );
  const lists = scopedLists.length
    ? scopedLists
    : Array.from(item.querySelectorAll(":scope ul"));
  for (const list of lists) {
    const roleItems = Array.from(list.children).filter((el) => el.tagName === "LI");
    if (!roleItems.length) continue;
    const hasEntity = roleItems.some((role) =>
      role.querySelector(":scope > div[data-view-name='profile-component-entity']")
    );
    if (!hasEntity) continue;
    const hasTitle = roleItems.some((role) =>
      getBoldText(getHeaderRow(getEntityContainer(role)))
    );
    if (hasTitle) return { list, roleItems };
  }
  return null;
}

function getExperienceEntries() {
  const section = getExperienceSection();
  if (!section) return [];

  let items = getTopExperienceItems(section);
  if (!items.length) {
    items = Array.from(section.querySelectorAll("li"));
  }

  const entries = [];

  items.forEach((item) => {
    const nestedRoles = findNestedRoleList(item);
    const entity = getEntityContainer(item);
    const headerRow = getHeaderRow(entity);
    const headerScope = headerRow || entity || item;
    if (nestedRoles) {
      const company =
        getBoldText(headerScope, nestedRoles.list) ||
        getCompanyLinkText(headerScope, nestedRoles.list) ||
        "";
      const companyLinkedinUrl = getCompanyLinkUrl(headerScope, nestedRoles.list);
      nestedRoles.roleItems.forEach((nested) => {
        const nestedEntity = getEntityContainer(nested);
        const nestedHeader = getHeaderRow(nestedEntity);
        const nestedScope = nestedHeader || nestedEntity || nested;
        const title = getBoldText(nestedScope);
        const employmentType = getCompanyLineText(nestedScope);
        const dateText = getDateLineText(nestedScope);
        if (!title) return;
        entries.push({
          title,
          company,
          employmentType,
          dateText,
          companyLinkedinUrl,
        });
      });
      return;
    }

    const title = getBoldText(headerScope);
    const companyLine = getCompanyLineText(headerScope);
    const split = splitCompanyAndEmployment(companyLine);
    const company = split.company || getCompanyLinkText(headerScope);
    const employmentType = split.employmentType;
    const dateText = getDateLineText(headerScope);
    const companyLinkedinUrl = getCompanyLinkUrl(headerScope);
    if (!title && !company) return;
    entries.push({
      title,
      company,
      employmentType,
      dateText,
      companyLinkedinUrl,
    });
  });

  return entries;
}

function joinUnique(values) {
  const seen = new Set();
  const result = [];
  values.forEach((value) => {
    const text = normalizeText(value);
    if (!text || seen.has(text)) return;
    seen.add(text);
    result.push(text);
  });
  return result.join(" | ");
}

function firstNonEmpty(values) {
  for (const value of values) {
    const text = normalizeText(value);
    if (text) return text;
  }
  return "";
}

function getExperiencePreview() {
  const entries = getExperienceEntries();
  if (!entries.length) {
    return { jobTitle: "", company: "", employmentType: "", companyLinkedinUrl: "" };
  }

  const currentEntries = entries.filter((entry) => isCurrentRole(entry.dateText));
  const chosen = currentEntries.length ? currentEntries : [entries[0]];

  return {
    jobTitle: joinUnique(chosen.map((entry) => entry.title)),
    company: joinUnique(chosen.map((entry) => entry.company)),
    employmentType: joinUnique(chosen.map((entry) => entry.employmentType)),
    companyLinkedinUrl: firstNonEmpty(
      chosen.map((entry) => entry.companyLinkedinUrl)
    ),
  };
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
  const experience = getExperiencePreview();
  return {
    name,
    avatarUrl,
    linkedinUrl: getCanonicalUrl(),
    jobTitle: experience.jobTitle,
    company: experience.company,
    employmentType: experience.employmentType,
    companyLinkedinUrl: experience.companyLinkedinUrl,
  };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "getProfilePreview") {
    sendResponse(getProfilePreview());
    return true;
  }
  return false;
});
