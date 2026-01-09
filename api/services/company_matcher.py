from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from models import Company

_LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "llc",
    "l.l.c",
    "ltd",
    "limited",
    "plc",
    "gmbh",
    "ag",
    "sa",
    "s.a",
    "srl",
    "bv",
    "oy",
    "oyj",
    "ab",
    "pte",
    "pty",
    "sas",
    "spa",
}


def normalize_company_name(name: Optional[str]) -> str:
    if not name:
        return ""
    text = re.split(r"\s*·\s*", name)[0]
    text = re.sub(r"\(.*?\)", "", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [token for token in text.split() if token and token not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def normalize_company_linkedin_url(raw_url: Optional[str]) -> Optional[str]:
    if not raw_url:
        return None
    url = raw_url.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parts = urlsplit(url)
    host = (parts.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    segments = [segment for segment in (parts.path or "").split("/") if segment]
    if "company" not in segments:
        return None
    index = segments.index("company")
    if index + 1 >= len(segments):
        return None
    slug = segments[index + 1]
    return urlunsplit(("https", "www.linkedin.com", f"/company/{slug}", "", ""))


def _extract_company_slug(url: Optional[str]) -> Optional[str]:
    normalized = normalize_company_linkedin_url(url)
    if not normalized:
        return None
    parts = urlsplit(normalized)
    segments = [segment for segment in (parts.path or "").split("/") if segment]
    if len(segments) < 2:
        return None
    return segments[1]


def _token_set(text: str) -> set[str]:
    return {token for token in text.split() if token}


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _score_company_match(
    candidate: Company, name_norm: str, linkedin_url_norm: Optional[str]
) -> int:
    if linkedin_url_norm:
        candidate_url = normalize_company_linkedin_url(
            getattr(candidate, "linkedin_url", None)
        )
        if candidate_url and candidate_url == linkedin_url_norm:
            return 100

    candidate_norm = normalize_company_name(getattr(candidate, "company_name", None))
    if candidate_norm and name_norm:
        if candidate_norm == name_norm:
            return 90
        if _token_set(candidate_norm) == _token_set(name_norm):
            return 88
        if _similarity(candidate_norm, name_norm) >= 0.93:
            return 85

    return 0


async def find_company_match(
    name: Optional[str], linkedin_url: Optional[str]
) -> Optional[Company]:
    name_norm = normalize_company_name(name)
    url_norm = normalize_company_linkedin_url(linkedin_url)
    candidates: list[Company] = []

    slug = _extract_company_slug(url_norm)
    if slug:
        candidates = await Company.filter(linkedin_url__icontains=slug).all()

    if not candidates and name:
        candidates = await Company.filter(company_name__iexact=name).all()

    if not candidates and name_norm:
        tokens = name_norm.split()
        token = max(tokens, key=len) if tokens else ""
        if token:
            candidates = await Company.filter(company_name__icontains=token).all()

    best: Optional[Company] = None
    best_score = 0
    second_score = 0
    for candidate in candidates:
        score = _score_company_match(candidate, name_norm, url_norm)
        if score > best_score:
            second_score = best_score
            best_score = score
            best = candidate
        elif score > second_score:
            second_score = score

    if best_score >= 90:
        return best
    if best_score >= 85 and (best_score - second_score) >= 5:
        return best

    return None
