from __future__ import annotations
from typing import Dict, Any, List

from helpers_deliverability import (
    count_words,
    find_spammy_phrases,
)

from helpers_clarity import (
    count_cta_phrases,
    count_question_marks,
    is_too_long_for_email,
    split_paragraphs,
    paragraph_word_counts,
    sentence_lengths,
    has_greeting,
    has_signoff,
    has_bullets,
    max_line_length,
    subject_word_count,
    subject_body_overlap_ratio,
)

from phrases import (
    CTA_PHRASES,
    COLD_OUTREACH_CLICHES,
)

from clarity_thresholds import (
    VERY_SHORT_EMAIL_WORDS,
    QUITE_SHORT_EMAIL_WORDS,
    DEFAULT_MAX_COLD_EMAIL_WORDS,
    SINGLE_PARA_BLOCK_WORDS,
    WALL_OF_TEXT_PARA_WORDS,
    MAX_PARAGRAPHS,
    AVG_SENT_LONG_THRESHOLD,
    MAX_SENT_LENGTH_THRESHOLD,
    CHOPPY_SENT_AVG_THRESHOLD,
    MAX_QUESTIONS_BEFORE_PENALTY,
    MAX_CTA_PHRASES_BEFORE_PENALTY,
    SUBJECT_SINGLE_WORD_THRESHOLD,
    SUBJECT_LONG_WORD_THRESHOLD,
    MIN_SUBJECT_WORDS_FOR_MISMATCH_CHECK,
    MAX_LINE_LENGTH_BEFORE_PENALTY,
    SINGLE_PARA_NO_BREAKS_THRESHOLD,
    MAX_CLICHE_PENALTY,
    CLICHE_PENALTY_PER_HIT,
)


def score_structure_and_clarity(
    subject: str,
    body: str,
    max_words_for_cold_email: int = DEFAULT_MAX_COLD_EMAIL_WORDS,
) -> Dict[str, Any]:
    """
    Structural and clarity score for an outbound email.

    Contract:
      - score is in [1, 7] for any email with a non-empty body
      - score is None only when there is no body to evaluate
      - missing subject is recorded but not penalised

    Notes:
      - subject_body_overlap_ratio is purely lexical (token overlap),
        not a measure of personalization depth.
    """
    subject = subject or ""
    body = body or ""

    issues: List[str] = []

    # Basic counts
    word_count = count_words(body)
    subject_wc = subject_word_count(subject)

    # Hard fail: nothing to work with
    if word_count == 0:
        return {
            "score": None,
            "fail_reason": "empty_body",
            "issues": ["empty_body"],
            "word_count": 0,
            "subject_word_count": subject_wc,
        }

    # Paragraphs
    paragraphs = split_paragraphs(body)
    paragraph_count = len(paragraphs)
    para_word_counts = paragraph_word_counts(paragraphs)
    max_para_words = max(para_word_counts) if para_word_counts else 0

    # Sentences
    sent_lens = sentence_lengths(body)
    avg_sent_len = (sum(sent_lens) / len(sent_lens)) if sent_lens else 0.0
    max_sent_len = max(sent_lens) if sent_lens else 0
    sent_len_std = (
        (sum((l - avg_sent_len) ** 2 for l in sent_lens) / len(sent_lens)) ** 0.5
        if sent_lens
        else 0.0
    )

    # CTA / questions
    cta_phrase_hits = count_cta_phrases(
        body,
        CTA_PHRASES,
        include_question_marks=False,
    )
    question_count = count_question_marks(body)

    # Layout / header / footer
    greeting = has_greeting(body)
    signoff = has_signoff(body)
    bullets = has_bullets(body)
    longest_line = max_line_length(body)

    # Subject vs body (lexical overlap only)
    overlap_ratio = subject_body_overlap_ratio(subject, body)

    # Clichés
    cliche_hits = find_spammy_phrases(body, COLD_OUTREACH_CLICHES)
    total_cliches = sum(cliche_hits.values())

    # Start at 100 and subtract penalties
    score_raw = 100.0

    # Length: aim roughly for 40–120 words
    if word_count < VERY_SHORT_EMAIL_WORDS:
        score_raw -= 8
        issues.append("very_short_email")
    elif word_count < QUITE_SHORT_EMAIL_WORDS:
        score_raw -= 3
        issues.append("quite_short_email")

    if is_too_long_for_email(body, max_words=max_words_for_cold_email):
        score_raw -= 12
        issues.append("too_long_for_cold_email")

    # Paragraphs
    if paragraph_count == 1 and word_count > SINGLE_PARA_BLOCK_WORDS and not bullets:
        score_raw -= 10
        issues.append("single_block_of_text")

    if max_para_words > WALL_OF_TEXT_PARA_WORDS:
        score_raw -= 12
        issues.append("wall_of_text_paragraph")

    if paragraph_count > MAX_PARAGRAPHS:
        score_raw -= 5
        issues.append("too_many_paragraphs")

    # Sentence shape
    if avg_sent_len > AVG_SENT_LONG_THRESHOLD:
        score_raw -= 10
        issues.append("average_sentence_too_long")

    if max_sent_len > MAX_SENT_LENGTH_THRESHOLD:
        score_raw -= 8
        issues.append("very_long_sentence")

    if avg_sent_len < CHOPPY_SENT_AVG_THRESHOLD and len(sent_lens) >= 3:
        score_raw -= 4
        issues.append("sentences_too_choppy")

    # CTA and focus (CTA phrases only, not all questions)
    if cta_phrase_hits == 0:
        score_raw -= 8
        issues.append("no_clear_cta")
    elif cta_phrase_hits > MAX_CTA_PHRASES_BEFORE_PENALTY:
        score_raw -= 5
        issues.append("too_many_asks")

    if question_count > MAX_QUESTIONS_BEFORE_PENALTY:
        score_raw -= 3
        issues.append("too_many_questions")

    # Greeting / signoff
    if not greeting:
        score_raw -= 3
        issues.append("missing_greeting")

    if not signoff:
        score_raw -= 2
        issues.append("missing_signoff")

    # Subject handling (recorded but not penalised when missing)
    if subject_wc == 0:
        issues.append("missing_subject")
        used_overlap = 1.0  # avoid mismatch penalty in scoring when there's no subject
    else:
        used_overlap = overlap_ratio

        if subject_wc == SUBJECT_SINGLE_WORD_THRESHOLD:
            score_raw -= 4
            issues.append("subject_too_short")
        elif subject_wc > SUBJECT_LONG_WORD_THRESHOLD:
            score_raw -= 4
            issues.append("subject_too_long")

        # Only penalise obvious mismatch on longer subjects
        if subject_wc >= MIN_SUBJECT_WORDS_FOR_MISMATCH_CHECK and used_overlap < 0.15:
            score_raw -= 4
            issues.append("subject_body_misaligned")

    # Skimmability
    if longest_line > MAX_LINE_LENGTH_BEFORE_PENALTY:
        score_raw -= 4
        issues.append("very_long_lines")

    if (
        not bullets
        and paragraph_count == 1
        and word_count > SINGLE_PARA_NO_BREAKS_THRESHOLD
    ):
        score_raw -= 4
        issues.append("no_breaks_or_bullets")

    # Generic outreach language
    if total_cliches > 0:
        score_raw -= min(MAX_CLICHE_PENALTY, total_cliches * CLICHE_PENALTY_PER_HIT)
        issues.append("generic_cold_outreach_language")

    # Clamp and map to 1–7
    score_raw = max(0.0, min(100.0, score_raw))
    band = (round((score_raw / 100.0) * 6.0)) + 1

    return {
        "score": band,
        "fail_reason": None,
        "issues": issues,
        "word_count": word_count,
        "subject_word_count": subject_wc,
        "paragraph_count": paragraph_count,
        "max_paragraph_word_count": max_para_words,
        "avg_sentence_length": avg_sent_len,
        "max_sentence_length": max_sent_len,
        "sentence_length_std": sent_len_std,
        "question_count": question_count,
        "cta_score": cta_phrase_hits,
        "has_greeting": greeting,
        "has_signoff": signoff,
        "has_bullets": bullets,
        "max_line_length": longest_line,
        "subject_body_overlap": overlap_ratio,  # raw lexical overlap as a metric
        "cliche_count": total_cliches,
    }
