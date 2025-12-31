#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict, Optional, Tuple
import json

from valueprop_prompt import build_valueprop_prompt
from llm_client import call_llm


def score_email_value_prop(
    lead: Dict[str, str],
    email_text: str,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Build the value-prop prompt, call the LLM, and normalize:
    - score: 1..7 or None if model returns "none" or invalid
    - feedback: None for score == 7, otherwise a single short sentence
    """
    prompt = build_valueprop_prompt(lead, email_text)
    raw = call_llm(prompt)

    try:
        data = json.loads(raw)
    except Exception:
        return None, "Model returned invalid JSON"

    raw_score = data.get("score")
    feedback = data.get("feedback", "")

    # normalize score
    score: Optional[int]
    if isinstance(raw_score, str) and raw_score.lower() == "none":
        score = None
    elif isinstance(raw_score, (int, float)):
        s = int(raw_score)
        if 1 <= s <= 7:
            score = s
        else:
            score = None
    else:
        score = None

    # normalize feedback
    if score == 7:
        feedback_out: Optional[str] = None
    else:
        if isinstance(feedback, str) and feedback.strip():
            text = feedback.strip()
            first_period = text.find(".")
            if first_period != -1:
                text = text[: first_period + 1]
            feedback_out = text[:200].strip()
        else:
            feedback_out = None

    return score, feedback_out
