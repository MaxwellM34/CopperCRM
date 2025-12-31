#!/usr/bin/env python3

from __future__ import annotations

from typing import Dict, Any, Optional, Tuple, List

from clarity_scoring import score_structure_and_clarity
from deliverability_scoring import score_deliverability
from valueprop_scorer import score_email_value_prop
from customer_reaction_scorer import score_email_customer_reaction


SCORING_VERSION = "v001"


def get_scoring_version() -> str:
    """Expose a simple version string so runs are traceable."""
    return SCORING_VERSION


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def extract_subject_body(text: str) -> Tuple[Optional[str], str]:
    """
    Split raw email text into subject + body.

    Behavior:
      - ONLY treat a line that starts with 'Subject:' (case-insensitive)
        as the subject.
      - If no such line exists, subject is None and the entire text is body.
    """
    if not text:
        return None, ""

    lines = text.splitlines()

    subject: Optional[str] = None
    subject_line_index: Optional[int] = None

    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            raw = line.split(":", 1)[1].strip()
            subject = raw if raw else None
            subject_line_index = i
            break

    if subject_line_index is not None:
        body_lines = lines[subject_line_index + 1 :]
        body = "\n".join(body_lines).strip()
        return subject, body

    # No explicit Subject: line found
    return None, text.strip()


def _show(v: Any) -> str:
    """
    Format value for human-readable output.

    IMPORTANT:
      - If v is None, we return the literal string "None".
      - No 'N/A', no blanks.
    """
    return "None" if v is None else str(v)


# -------------------------------------------------------------------
# Core API
# -------------------------------------------------------------------

def score_email(lead: Dict[str, Any], email_text: str) -> Dict[str, Any]:
    """
    Unified scoring entrypoint for pipeline + tools.

    Inputs:
      - lead: dict for this contact (row from imported_leads, etc.)
      - email_text: final email text (subject may or may not be included)

    Outputs a dict with ONLY individual scores, no combined overall:
      {
        "subject": str|None,
        "body": str,
        "clarity": {...},
        "deliverability": {...},
        "valueprop_score": int|None,
        "valueprop_feedback": str|None,
        "customer_reaction_score": int|None,
        "customer_reaction_feedback": str|None,
        "sub_scores": {
            "clarity": int|None,
            "deliverability": int|None,
            "value_prop": int|None,
            "customer_reaction": int|None,
        },
      }
    """
    subject, body = extract_subject_body(email_text)

    # Scorers that expect strings: pass "" if subject is None
    subject_for_scoring = subject or ""

    # 1) Clarity / structure (heuristic)
    clarity = score_structure_and_clarity(subject_for_scoring, body)
    clarity_score: Optional[int] = clarity.get("score")

    # 2) Deliverability / spamminess (heuristic)
    deliverability = score_deliverability(subject_for_scoring, body)
    deliverability_score: Optional[int] = deliverability.get("score")

    # 3) Value-prop fit (LLM) – use full body text
    vp_score, vp_feedback = score_email_value_prop(lead, body)

    # 4) Customer reaction / perceived usefulness (LLM)
    cr_score, cr_feedback = score_email_customer_reaction(lead, body)

    sub_scores = {
        "clarity": clarity_score,
        "deliverability": deliverability_score,
        "value_prop": vp_score,
        "customer_reaction": cr_score,
    }

    # NO overall score here. Just raw individual scores.
    return {
        "subject": subject,
        "body": body,
        "clarity": clarity,
        "deliverability": deliverability,
        "valueprop_score": vp_score,
        "valueprop_feedback": vp_feedback,
        "customer_reaction_score": cr_score,
        "customer_reaction_feedback": cr_feedback,
        "sub_scores": sub_scores,
    }


def format_scoring_output(scores: Dict[str, Any]) -> str:
    """
    Pretty-print scoring results into a .txt report.

    Behavior:
      - NO overall score.
      - Any None values show up as the literal text "None".
    """
    sub = scores.get("sub_scores", {}) or {}
    clarity = scores.get("clarity", {}) or {}
    deliver = scores.get("deliverability", {}) or {}
    vp_fb = scores.get("valueprop_feedback")
    cr_fb = scores.get("customer_reaction_feedback")

    lines: List[str] = []

    # --- Summary -----------------------------------------------------
    lines.append("=== EMAIL SCORING SUMMARY ===")
    lines.append("")

    # --- Sub-scores ONLY ---------------------------------------------
    lines.append("Sub-scores:")
    lines.append(f"  - Structure / clarity:   {_show(sub.get('clarity'))}")
    lines.append(f"  - Deliverability / spam: {_show(sub.get('deliverability'))}")
    lines.append(f"  - Value proposition:     {_show(sub.get('value_prop'))}")
    lines.append(f"  - Customer reaction:     {_show(sub.get('customer_reaction'))}")
    lines.append("")

    # --- Short feedback from LLM scorers -----------------------------
    if vp_fb:
        lines.append("Value-prop feedback:")
        lines.append(f"  {vp_fb}")
        lines.append("")

    if cr_fb:
        lines.append("Customer reaction feedback:")
        lines.append(f"  {cr_fb}")
        lines.append("")

    # --- Clarity details ---------------------------------------------
    if clarity:
        word_count = clarity.get("word_count")
        para_count = clarity.get("paragraph_count")
        avg_len = clarity.get("avg_sentence_length")
        try:
            avg_len_str = f"{float(avg_len):.1f}"
        except (TypeError, ValueError):
            avg_len_str = _show(avg_len)

        lines.append("Clarity details:")
        lines.append(
            f"  Words: {_show(word_count)} | "
            f"Paragraphs: {_show(para_count)} | "
            f"Avg sentence length: {avg_len_str}"
        )

        issues = clarity.get("issues")
        if isinstance(issues, list):
            issue_text = ", ".join(issues) if issues else "None"
        else:
            issue_text = _show(issues)
        lines.append(f"  Issues: {issue_text}")
        lines.append("")

    # --- Deliverability details --------------------------------------
    if deliver:
        d_word_count = deliver.get("word_count")
        link_count = deliver.get("link_count")
        html_tags = deliver.get("html_tag_count")

        lines.append("Deliverability details:")
        lines.append(
            f"  Words: {_show(d_word_count)} | "
            f"Links: {_show(link_count)} | "
            f"HTML tags: {_show(html_tags)}"
        )

        d_issues = deliver.get("issues")
        if isinstance(d_issues, list):
            d_issue_text = ", ".join(d_issues) if d_issues else "None"
        else:
            d_issue_text = _show(d_issues)
        lines.append(f"  Issues: {d_issue_text}")

        fail_reason = deliver.get("fail_reason")
        if fail_reason is not None:
            lines.append(f"  Fail reason: {_show(fail_reason)}")

        lines.append("")

    lines.append(f"(Scoring version: {SCORING_VERSION})")
    return "\n".join(lines)
