"""
Phrase lists for evaluating the deliverability and perceived 'spaminess'
of outbound B2B emails (e.g., Kraken Sense wastewater / lab services outreach).

These lists are designed to work with helpers in helpers.py:
- find_spammy_phrases(text, spammy_phrases)
- count_cta_phrases(text, cta_phrases)
- has_personalization_token(text, tokens)
"""

# ---------------------------------------------------------------------------
# Phrases that are basically never appropriate in serious B2B / public health
# ---------------------------------------------------------------------------

HARD_FAIL_PHRASES = [
    "no strings attached",
    "no questions asked",
    "100% guaranteed",
    "guaranteed results",
    "zero risk",
    "risk free",
]


# ---------------------------------------------------------------------------
# Overly salesy / hypey language that hurts trust if overused
# ---------------------------------------------------------------------------

HIGH_RISK_SALESY_PHRASES = [
    "game changer",
    "revolutionize your workflow",
    "revolutionize your operations",
    "cutting edge solution",
    "state of the art platform",
    "next generation platform",
    "unlock new revenue",
    "skyrocket your roi",
    "explode your growth",
    "turbocharge your operations",
    "maximize your profits",
    "boost your revenue",
    "supercharge your results",
]


# ---------------------------------------------------------------------------
# Generic cold outreach cliches / AI-ish filler
# (not forbidden, but too many = low quality vibes)
# ---------------------------------------------------------------------------

COLD_OUTREACH_CLICHES = [
    "hope this email finds you well",
    "hope you are doing well",
    "i know you are busy",
    "just reaching out",
    "just wanted to reach out",
    "just following up",
    "just circling back",
    "circling back on this",
    "bumping this to the top of your inbox",
    "gentle reminder",
    "quick bump",
    "as a quick reminder",
    "not sure if you saw my last email",
    "not sure if this reached you",
    "touching base",
    "checking in on this",
]


# ---------------------------------------------------------------------------
# Pressure / urgency language
# ---------------------------------------------------------------------------

PRESSURE_PHRASES = [
    "now is the perfect time",
    "you don't want to miss this",
    "you do not want to miss this",
    "time sensitive opportunity",
    "urgent opportunity",
    "act now",
]


# ---------------------------------------------------------------------------
# Red-flag claims for a diagnostics / wastewater / health context
# ---------------------------------------------------------------------------

HEALTH_CLAIM_RED_FLAGS = [
    "eliminate all pathogens",
    "eliminates all pathogens",
    "zero pathogens guaranteed",
    "completely eliminates risk",
    "completely remove risk",
    "100% detection in all cases",
    "detects every pathogen",
    "never misses a pathogen",
    "fully replaces your lab testing",
    "no need for a certified lab",
    "no need for laboratory testing",
    "guaranteed regulatory compliance",
    "guaranteed compliance",
]


# ---------------------------------------------------------------------------
# Call-to-action phrases for count_cta_phrases
# (not bad; you just want to know how many you stacked)
# ---------------------------------------------------------------------------

CTA_PHRASES = [
    "chat",
    "would you be open to a quick call",
    "would you be open to a quick chat",
    "would you be open to a brief call",
    "could we set up a quick call",
    "can we set up a quick call",
    "can we set up a time to talk",
    "can we find 15 minutes",
    "could we find 15 minutes",
    "worth a quick chat",
    "worth a quick conversation",
    "schedule a quick demo",
    "schedule a demo",
    "book a time on my calendar",
    "book some time on my calendar",
    "grab 15 minutes",
    "jump on a quick call",
    "happy to send more details",
    "happy to share more details",
    "happy to share more",
    "let me know if you would like to learn more",
    "let me know if you would like more details",
    "let me know what you think",
    "does it make sense to explore",
    "does it make sense to chat",
    "are you the right person to speak with",
    "is there someone else on your team",
    "who is the best person to speak with",
]


# ---------------------------------------------------------------------------
# Greeting and signoff detection (moved from helpers_clarity)
# ---------------------------------------------------------------------------

GREETING_PREFIXES = [
    "hi ",
    "hey ",
    "hello ",
    "dear ",
]

SIGNOFF_PREFIXES = [
    "best",
    "thanks",
    "thank you",
    "cheers",
    "sincerely",
    "regards",
    "kind regards",
]

# ---------------------------------------------------------------------------
# Stopwords for subject-body overlap
# ---------------------------------------------------------------------------

STOPWORDS_FOR_OVERLAP = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in",
    "on", "at", "with", "from", "by", "about",
    "this", "that", "these", "those",
    "your", "our", "my", "we", "you", "i",
}




