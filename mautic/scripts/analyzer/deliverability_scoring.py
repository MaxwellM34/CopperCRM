from __future__ import annotations
from typing import Optional, Dict, Any, List

from helpers_deliverability import (
    detect_links,
    count_words,
    detect_html_tag_count,
    find_spammy_phrases,
    count_exclamation_marks,
    count_all_caps_words,
    has_non_ascii,
    is_plain_text_email,
    contains_prohibited_unicode,
    normalize_to_ascii,
)

from phrases import (
    HARD_FAIL_PHRASES,
    HIGH_RISK_SALESY_PHRASES,
    COLD_OUTREACH_CLICHES,
    PRESSURE_PHRASES,
    HEALTH_CLAIM_RED_FLAGS,
)

from deliverability_thresholds import (
    MAX_LINKS_BEFORE_RISK,
    HARD_WORD_LIMIT,
    MAX_HTML_TAGS_BEFORE_RISK,
    HEAVY_HTML_TAG_THRESHOLD,
    MAX_EXCLAMATIONS_BEFORE_RISK,
    MAX_CAPS_WORDS_BEFORE_RISK,
)


def score_deliverability(subject: str, body: str) -> Dict[str, Any]:
    """
    Deliverability / spam-risk score for outbound email.

    Contract:
      - score is in [1, 7] for messages that are technically sendable
        (7 = lowest risk, 1 = highest risk)
      - score is None only for clearly unsafe or unusable content
        (e.g. hard health claims, extreme length)

    Internally:
      - start from 100 and subtract penalties for risky features
      - clamp score_raw to [0, 100]
      - map 0–100 to 1–7 band (100 -> 7, 0 -> 1)
    """
    raw_subject = subject or ""
    raw_body = body or ""
    raw_text = raw_subject + "\n" + raw_body

    # Basic presence of non-ASCII (for metrics only)
    non_ascii = has_non_ascii(raw_text)

    # Normalised text for detection
    subject_norm = normalize_to_ascii(raw_subject)
    body_norm = normalize_to_ascii(raw_body)
    text = subject_norm + "\n" + body_norm

    # Features
    links = detect_links(text)
    link_count = len(links)
    word_count = count_words(text)
    html_tag_count = detect_html_tag_count(text)
    plain_text = is_plain_text_email(subject_norm, body_norm)

    hard_fail_hits = find_spammy_phrases(text, HARD_FAIL_PHRASES)
    health_claim_hits = find_spammy_phrases(text, HEALTH_CLAIM_RED_FLAGS)
    salesy_hits = find_spammy_phrases(text, HIGH_RISK_SALESY_PHRASES)
    cliche_hits = find_spammy_phrases(text, COLD_OUTREACH_CLICHES)
    pressure_hits = find_spammy_phrases(text, PRESSURE_PHRASES)

    exclamations = count_exclamation_marks(text)
    caps_words = count_all_caps_words(text, min_length=4)

    fail_reason: Optional[str] = None
    issues: List[str] = []

    # Hard fail: only for clearly unsafe / non-compliant / unusable texts
    if hard_fail_hits:
        fail_reason = "hard_fail_phrases"
        issues.append("hard_fail_phrases")
    elif health_claim_hits:
        fail_reason = "health_claim_phrases"
        issues.append("health_claim_phrases")
    elif word_count >= HARD_WORD_LIMIT:
        fail_reason = "too_long_total_words"
        issues.append("too_long_total_words")

    if fail_reason is not None:
        return {
            "score": None,
            "fail_reason": fail_reason,
            "issues": issues,
            "word_count": word_count,
            "link_count": link_count,
            "html_tag_count": html_tag_count,
            "salesy_count": len(salesy_hits),
            "cliche_count": len(cliche_hits),
            "pressure_count": len(pressure_hits),
            "exclamations": exclamations,
            "caps_words": caps_words,
            "non_ascii": non_ascii,
        }

    # Start at 100 and subtract risk penalties
    score_raw = 100.0

    # Phrase-based penalties
    if salesy_hits:
        # High-risk sales language
        score_raw -= 12.0 * len(salesy_hits)
        issues.append("salesy_language")

    if pressure_hits:
        # Time/urgency pressure, "last chance", etc.
        score_raw -= 12.0 * len(pressure_hits)
        issues.append("pressure_language")

    if cliche_hits:
        # Generic outreach clichés
        score_raw -= 5.0 * len(cliche_hits)
        issues.append("generic_cold_outreach_language")

    # Links: beyond max_links, subtract more as count increases
    if link_count > MAX_LINKS_BEFORE_RISK:
        score_raw -= (link_count - MAX_LINKS_BEFORE_RISK) * 6.0
        issues.append("high_link_count")

    # HTML: prefer mostly-plain text
    if not plain_text and html_tag_count > MAX_HTML_TAGS_BEFORE_RISK:
        score_raw -= 5.0
        issues.append("html_email")

    if html_tag_count > HEAVY_HTML_TAG_THRESHOLD:
        score_raw -= 20.0
        issues.append("heavy_html")

    # Shouting / formatting
    if exclamations > MAX_EXCLAMATIONS_BEFORE_RISK:
        score_raw -= (exclamations - MAX_EXCLAMATIONS_BEFORE_RISK) * 2.0
        issues.append("many_exclamations")

    if caps_words > MAX_CAPS_WORDS_BEFORE_RISK:
        score_raw -= (caps_words - MAX_CAPS_WORDS_BEFORE_RISK) * 3.0
        issues.append("many_all_caps_words")

    # Unicode: treat as risk, not auto-fail
    if contains_prohibited_unicode(raw_text):
        score_raw -= 20.0
        issues.append("risky_unicode")

    # Clamp 0–100
    score_raw = max(0.0, min(100.0, score_raw))

    # Map 0–100 → 1–7 band (100 -> 7, 0 -> 1)
    band = int(round((score_raw / 100.0) * 6.0)) + 1
    band = max(1, min(7, band))

    return {
        "score": band,
        "fail_reason": None,
        "issues": issues,
        "word_count": word_count,
        "link_count": link_count,
        "html_tag_count": html_tag_count,
        "salesy_count": len(salesy_hits),
        "cliche_count": len(cliche_hits),
        "pressure_count": len(pressure_hits),
        "exclamations": exclamations,
        "caps_words": caps_words,
        "non_ascii": non_ascii,
    }
