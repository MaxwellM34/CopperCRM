from __future__ import annotations

import re
from typing import Literal

from gender_guesser.detector import Detector

Gender = Literal["male", "female", "unknown_gender"]

_detector = Detector(case_sensitive=False)


def _normalize_first_name(name: str | None) -> str | None:
    if not name:
        return None
    token = re.split(r"[\\s,/]+", name.strip())[0]
    token = re.sub(r"[^A-Za-z]", "", token)
    token = token.lower()
    return token or None


def infer_gender_by_name(first_name: str | None) -> Gender:
    """
    Use a ~40k-name detector to assign gender.
    Returns one of: male, female, or unknown_gender (for andy/mostly/unknown).
    """
    name = _normalize_first_name(first_name)
    if not name:
        return "unknown_gender"
    result = _detector.get_gender(name)
    if result in {"male", "mostly_male"}:
        return "male"
    if result in {"female", "mostly_female"}:
        return "female"
    return "unknown_gender"


# Backfill helper
from models import Lead  # noqa: E402  (tortoise models depend on settings)


async def backfill_lead_genders() -> int:
    """
    Assign genders for any leads that are currently unknown.
    Returns number of leads updated.
    """
    updated = 0
    async for lead in Lead.filter(gender="unknown_gender"):
        inferred = infer_gender_by_name(lead.first_name)
        if inferred != lead.gender:
            lead.gender = inferred
            await lead.save(update_fields=["gender"])
            updated += 1
    return updated
