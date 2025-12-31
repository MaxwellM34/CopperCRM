'''
Helper functions for evaluating the deliverability and 'spaminess' of an outbound email.
These are functions that can be reused inside classes or scripts individually.
'''

from __future__ import annotations
import re
import unicodedata   # <- add this
from typing import List, Dict


# --- Regexes -----------------------------------------------------------------

#Look for URLs
LINK_REGEX = re.compile(
    r"""(?ix)   
    \b(?:https?://|www\.)[^\s<>"']+   
    """
)

#Look for HTML tags
HTML_TAG_REGEX = re.compile(r"<\/?[a-z][^>]*>", re.IGNORECASE)

#Look for normal words
WORD_REGEX = re.compile(r"\b\w+\b")


# --- Core helper functions ---------------------------------------------------

def detect_links(text: str) -> List[str]:
    '''
    Return a list of URL-like substrings in the text.
    '''
    if not text: 
        return []
    return LINK_REGEX.findall(text)

def count_words(text: str) -> int:
    '''
    Rough word count
    '''
    if not text:
        return 0 
    return len(WORD_REGEX.findall(text))

def detect_html_tag_count(text: str) -> int:
    '''
    Return number of HTML-like tags. 
    Any value > 0 suggests email is not plain text
    '''
    if not text: 
        return 0 
    return len(HTML_TAG_REGEX.findall(text))

def find_spammy_phrases(
        text: str,
        spammy_phrases: List[str],
) -> Dict[str, int]:
    '''
    Given a list of spammy phrases, return the count for any found.
    Case-insensitive, simple substring matching. Uses word boundaries to solve issue where
    'free' would match 'freeform'
    '''
    found: Dict[str, int] = {}
    if not text:
        return found
    
    for phrase in spammy_phrases:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        matches = re.findall(pattern, text, flags = re.IGNORECASE)
        if matches:
                found[phrase] = len(matches)

    return found

def is_plain_text_email(subject: str, body: str) -> bool:
    '''
    Heuristic: treat email as plain text if no HTML-like tags found
    '''
    combined = (subject or "") + "\n" + (body or "")
    return detect_html_tag_count(combined) == 0

# --- Extra text-shape helpers ------------------------------------------------

def strip_html_tags(text: str) -> str:
    """
    Remove HTML tags and return plain text.
    Useful for further analysis on HTML emails.
    """
    if not text:
        return ""
    return HTML_TAG_REGEX.sub("", text)


def count_exclamation_marks(text: str) -> int:
    """
    Count '!' characters as a proxy for shouty / hypey tone.
    """
    if not text:
        return 0
    return text.count("!")


def count_all_caps_words(text: str, min_length: int = 3) -> int:
    """
    Count words that are ALL CAPS (with at least min_length characters).
    Used to detect shouting or over-emphasis.
    """
    if not text:
        return 0
    words = WORD_REGEX.findall(text)
    return sum(
        1
        for w in words
        if len(w) >= min_length and w.isalpha() and w.upper() == w
    )


def has_non_ascii(text: str) -> bool:
    """
    True if text contains characters outside basic ASCII (codepoint > 127).

    NOTE:
    - This includes harmless things like curly quotes and non-breaking spaces.
    - You generally should NOT hard-fail on this alone.
    - Use `contains_prohibited_unicode` for stricter checks.
    """
    if not text:
        return False
    return any(ord(ch) > 127 for ch in text)


# Characters / ranges that are genuinely risky or undesirable in cold outbound.
# You can grow/shrink this list as you see how real emails behave.
PROHIBITED_UNICODE_CHARS = [
    "—",  # em dash
    "–",  # en dash
    "\u2022",  # bullet •
    "\u00b7",  # middle dot ·
]

# Emoji / pictograph ranges, etc.
PROHIBITED_UNICODE_RANGES = [
    (0x1F300, 0x1F5FF),  # Misc symbols and pictographs (many emoji)
    (0x1F600, 0x1F64F),  # Emoticons
    (0x1F680, 0x1F6FF),  # Transport & map symbols
    (0x2600, 0x26FF),    # Misc symbols (☀, ☎, etc.)
]


def contains_prohibited_unicode(text: str) -> bool:
    """
    True if text contains clearly risky unicode:
    - emoji / pictographs
    - em dash / en dash
    - bullets / special symbols (as defined above)

    This is what you should use for HARD FAIL conditions,
    not `has_non_ascii` by itself.
    """
    if not text:
        return False

    for ch in text:
        code = ord(ch)

        # Explicit chars
        if ch in PROHIBITED_UNICODE_CHARS:
            return True

        # Emoji / symbol ranges
        for start, end in PROHIBITED_UNICODE_RANGES:
            if start <= code <= end:
                return True

    return False


def normalize_to_ascii(text: str) -> str:
    """
    Normalize text to a best-effort ASCII approximation.

    - Curly quotes → straight quotes
    - Accented letters → base letters (é → e)
    - Many symbols removed entirely

    Use this *before* analysis if you want to strip most unicode noise
    while keeping the content readable.
    """
    if not text:
        return ""
    # NFKD decomposes characters; encode/decode with 'ignore' drops non-ASCII remnants
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii", "ignore")


