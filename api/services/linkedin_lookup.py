from typing import Optional, cast
from urllib.parse import urlsplit, urlunsplit

from models import Lead


def normalize_linkedin_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parts = urlsplit(url)
    host = (parts.netloc or "").lower()
    path = parts.path or ""
    if path and path != "/":
        path = path.rstrip("/")

    return urlunsplit(("https", host, path, "", ""))


def extract_linkedin_slug(raw_url: str) -> Optional[str]:
    normalized = normalize_linkedin_url(raw_url)
    if not normalized:
        return None
    path = urlsplit(normalized).path
    if not path:
        return None
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return None
    if parts[0] not in {"in", "pub"}:
        return None
    return parts[1]


def build_linkedin_variants(raw_url: str) -> list[str]:
    normalized = normalize_linkedin_url(raw_url)
    if not normalized:
        return []

    parts = urlsplit(normalized)
    host = parts.netloc
    path = parts.path or ""
    if path and not path.startswith("/"):
        path = f"/{path}"

    base_path = path.rstrip("/") if path else ""
    paths = {base_path, f"{base_path}/"} if base_path else {""}

    hosts = {host}
    if host.startswith("www."):
        hosts.add(host[len("www."):])
    else:
        hosts.add(f"www.{host}")

    variants: list[str] = []
    for host_value in hosts:
        for path_value in paths:
            url_path = path_value if path_value else ""
            variants.append(urlunsplit(("https", host_value, url_path, "", "")))
            variants.append(urlunsplit(("http", host_value, url_path, "", "")))
            if url_path:
                variants.append(f"{host_value}{url_path}")

    # Keep order while deduping
    seen = set()
    unique_variants = []
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        unique_variants.append(variant)
    return unique_variants


async def find_lead_by_linkedin(raw_url: str) -> Optional[Lead]:
    variants = build_linkedin_variants(raw_url)
    if variants:
        lead = (
            await Lead.filter(personal_linkedin__in=variants)
            .prefetch_related("company")
            .first()
        )
        if lead:
            return lead

    slug = extract_linkedin_slug(raw_url)
    if slug:
        lead = (
            await Lead.filter(personal_linkedin__icontains=f"/in/{slug}")
            .prefetch_related("company")
            .first()
        )
        if lead:
            return lead

    return None


def _get_optional_str(obj: object, attr: str) -> Optional[str]:
    value = cast(Optional[str], getattr(obj, attr, None))
    if value is None:
        return None
    value = value.strip()
    return value or None


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value:
            return value
    return None


def lead_to_profile(lead: Lead) -> dict[str, Optional[str]]:
    company_name = None
    company = getattr(lead, "company", None)
    if company is not None:
        company_name = _get_optional_str(company, "company_name")

    first_name = _get_optional_str(lead, "first_name") or ""
    last_name = _get_optional_str(lead, "last_name") or ""
    full_name = " ".join(part for part in [first_name, last_name] if part).strip()

    email = _first_non_empty(
        _get_optional_str(lead, "work_email"),
        _get_optional_str(lead, "email"),
    )
    location = _first_non_empty(
        _get_optional_str(lead, "person_address"),
        _get_optional_str(lead, "country"),
    )

    return {
        "name": full_name or None,
        "occupation": _get_optional_str(lead, "job_title"),
        "company": company_name,
        "email": email,
        "location": location,
        "linkedin_url": _get_optional_str(lead, "personal_linkedin"),
        "description": _get_optional_str(lead, "profile_summary"),
    }
