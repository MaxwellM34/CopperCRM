from __future__ import annotations

from typing import List, Set, Optional
import re

from helpers_deliverability import count_words
from phrases import GREETING_PREFIXES, SIGNOFF_PREFIXES, STOPWORDS_FOR_OVERLAP


# --- CTA / questions ---------------------------------------------------------


def count_cta_phrases(
    text: str,
    cta_phrases: List[str],
    include_question_marks: bool = True,
    max_question_mark_bonus: int = 2,
) -> int:
    """
    Count CTA phrases in the text, with an optional small bonus for question marks.
    Intended for clarity / focus scoring.
    """
    if not text:
        return 0

    lowered = text.lower()
    count = 0

    for phrase in cta_phrases:
        p = phrase.lower()
        if p and p in lowered:
            count += 1

    if include_question_marks:
        count += min(lowered.count("?"), max_question_mark_bonus)

    return count


def count_question_marks(text: str) -> int:
    """Return the number of '?' characters in the text."""
    if not text:
        return 0
    return text.count("?")


# --- Length & paragraphs -----------------------------------------------------


def is_too_long_for_email(text: str, max_words: int = 120) -> bool:
    """
    True if the word count exceeds max_words.
    Empty text is never treated as too long.
    """
    if not text:
        return False
    return count_words(text) > max_words


def split_paragraphs(body: str) -> List[str]:
    """
    Split body into paragraphs using blank lines as separators.
    Returns a list of non-empty, stripped paragraphs.
    """
    if not body:
        return []
    parts = re.split(r"\n\s*\n", body)
    return [p.strip() for p in parts if p and p.strip()]


def paragraph_word_counts(paragraphs: Optional[List[str]]) -> List[int]:
    """
    Return word counts for each paragraph.
    None or an empty list yields an empty list.
    """
    if not paragraphs:
        return []
    return [count_words(p or "") for p in paragraphs]


def sentence_lengths(text: str) -> List[int]:
    """
    Return a list of word counts per sentence, using a rough split
    on '.', '!' and '?'.
    """
    if not text:
        return []
    parts = re.split(r"[.!?]+", text)
    lengths: List[int] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lengths.append(count_words(part))
    return lengths


# --- Greeting / signoff / layout --------------------------------------------


def _non_empty_lines(text: str) -> List[str]:
    if not text:
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def has_greeting(body: str) -> bool:
    """
    Detect a simple greeting in the first non-empty line.
    GREETING_PREFIXES are defined in phrases.py.
    """
    lines = _non_empty_lines(body)
    if not lines:
        return False

    first = lines[0].lower()
    return first.startswith(tuple(GREETING_PREFIXES))


def has_signoff(body: str) -> bool:
    """
    Detect a signoff in the last few non-empty lines.
    SIGNOFF_PREFIXES are defined in phrases.py.
    """
    lines = _non_empty_lines(body)
    if not lines:
        return False

    # Look a bit further up to catch "Best," above name/title lines
    tail = [ln.lower().rstrip(",.! ") for ln in lines[-6:]]  # was [-3:] and not detecting signoff because of email sig
    for t in tail:
        for p in SIGNOFF_PREFIXES:
            if t == p or t.startswith(p + " "):
                return True

    return False



def has_bullets(body: str) -> bool:
    """
    Return True if any line looks like a bullet or numbered list item.
    """
    if not body:
        return False

    for ln in body.splitlines():
        stripped = ln.lstrip()
        if stripped.startswith(("-", "*")):
            return True
        if re.match(r"\d+\.", stripped):
            return True

    return False


def max_line_length(body: str) -> int:
    """
    Return the length of the longest line in the body.
    Empty input returns 0.
    """
    if not body:
        return 0
    return max((len(ln) for ln in body.splitlines()), default=0)


# --- Subject / body alignment -----------------------------------------------


def subject_word_count(subject: str) -> int:
    """Word count for the subject line."""
    if not subject:
        return 0
    return count_words(subject)


def _tokenize_words(text: str) -> List[str]:
    """
    Lowercase tokenization on word boundaries.
    Empty input returns an empty list.
    """
    if not text:
        return []
    return re.findall(r"\b\w+\b", text.lower())


def subject_body_overlap_ratio(
    subject: str,
    body: str,
    stopwords: Optional[Set[str]] = None,
) -> float:
    """
    Ratio of subject content words that also appear in the body.

    This measures simple lexical overlap, not personalization depth.
    Pronouns and generic function words are filtered via STOPWORDS_FOR_OVERLAP.
    """
    if not subject:
        return 0.0

    if stopwords is None:
        stopwords = STOPWORDS_FOR_OVERLAP

    subject_tokens = [
        t for t in _tokenize_words(subject)
        if t not in stopwords
    ]
    if not subject_tokens:
        return 0.0

    body_tokens = set(_tokenize_words(body))
    if not body_tokens:
        return 0.0

    shared = sum(1 for t in subject_tokens if t in body_tokens)
    return shared / float(len(subject_tokens))
