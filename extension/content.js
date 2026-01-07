function getCanonicalUrl() {
  return (
    document.querySelector("link[rel='canonical']")?.href ||
    window.location.href.split("?")[0]
  );
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
    "a[href*='/company/'] span[aria-hidden='true'], a[href*='/company/'] span.visually-hidden",
    excluded
  );
}

function getCompanyLineText(container, excluded) {
  return getTextFromSelector(
    container,
    "span.t-14.t-normal span[aria-hidden='true'], span.t-14.t-normal",
    excluded
  );
}

function getDateLineText(container) {
  const el =
    container.querySelector("span.t-14.t-normal.t-black--light span[aria-hidden='true']") ||
    container.querySelector("span.t-14.t-normal.t-black--light");
  return getTextFromElement(el);
}

function getRoleAnchor(container) {
  if (!container) return null;
  const anchors = Array.from(
    container.querySelectorAll("a.optional-action-target-wrapper")
  );
  if (anchors.length) {
    const nonExperience = anchors.find((anchor) => {
      const field = anchor.getAttribute("data-field") || "";
      return !field.startsWith("experience_");
    });
    return nonExperience || anchors[0];
  }
  return container.querySelector("a[href*='/company/']");
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
  const lists = Array.from(item.querySelectorAll(":scope ul"));
  for (const list of lists) {
    const roleItems = Array.from(list.children).filter((el) => el.tagName === "LI");
    if (!roleItems.length) continue;
    const hasExperienceField = roleItems.some((role) =>
      role.querySelector("a[data-field^='experience_']")
    );
    if (hasExperienceField) continue;
    const hasTitle = roleItems.some((role) => getBoldText(role));
    if (hasTitle) {
      return { list, roleItems };
    }
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
    if (nestedRoles) {
      const company =
        getBoldText(item, nestedRoles.list) ||
        getCompanyLinkText(item, nestedRoles.list) ||
        splitCompanyAndEmployment(getCompanyLineText(getRoleAnchor(item) || item, nestedRoles.list)).company;
      nestedRoles.roleItems.forEach((nested) => {
        const title = getBoldText(nested);
        const roleAnchor = getRoleAnchor(nested) || nested;
        const employmentType = getCompanyLineText(roleAnchor);
        const dateText = getDateLineText(roleAnchor);
        if (!title) return;
        entries.push({ title, company, employmentType, dateText });
      });
      return;
    }

    const title = getBoldText(item);
    const roleAnchor = getRoleAnchor(item) || item;
    const companyLine = getCompanyLineText(roleAnchor);
    const split = splitCompanyAndEmployment(companyLine);
    const company = split.company || getCompanyLinkText(item);
    const employmentType = split.employmentType;
    const dateText = getDateLineText(roleAnchor);
    if (!title && !company) return;
    entries.push({ title, company, employmentType, dateText });
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

function getExperiencePreview() {
  const entries = getExperienceEntries();
  if (!entries.length) {
    return { jobTitle: "", company: "", employmentType: "" };
  }

  const currentEntries = entries.filter((entry) => isCurrentRole(entry.dateText));
  const chosen = currentEntries.length ? currentEntries : [entries[0]];

  return {
    jobTitle: joinUnique(chosen.map((entry) => entry.title)),
    company: joinUnique(chosen.map((entry) => entry.company)),
    employmentType: joinUnique(chosen.map((entry) => entry.employmentType)),
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
  };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "getProfilePreview") {
    sendResponse(getProfilePreview());
    return true;
  }
  return false;
});
