from __future__ import annotations

import csv
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Sequence

from fastapi import HTTPException
from openai import AsyncOpenAI

from models import Company, FirstEmail, Lead, User, LLMProfile

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_PROMPT_TOKENS = 360
DEFAULT_COMPLETION_TOKENS = 240

MODEL_PRICING: dict[str, dict[str, Decimal]] = {
    # Prices per 1K tokens (USD) - adjust if you change models
    "gpt-4o-mini": {"input": Decimal("0.00015"), "output": Decimal("0.0006")},
    "gpt-4o": {"input": Decimal("0.0025"), "output": Decimal("0.005")},
}

HISTORICAL_PATHS = [
    Path("mautic/ai-leads/generated"),
    Path("mautic/generated"),
    Path("ai-leads/generated"),
]


def _pricing_for_model(model: str) -> dict[str, Decimal]:
    return MODEL_PRICING.get(model) or MODEL_PRICING["gpt-4o-mini"]


def estimate_cost_from_tokens(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    pricing = _pricing_for_model(model)
    prompt_cost = pricing["input"] * Decimal(prompt_tokens) / Decimal(1000)
    completion_cost = pricing["output"] * Decimal(completion_tokens) / Decimal(1000)
    total = prompt_cost + completion_cost
    return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _sanitize(value: str | None, max_length: int = 500) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) > max_length:
        return value[: max_length - 3] + "..."
    return value


def build_lead_context(lead: Lead) -> str:
    company: Company | None = getattr(lead, "company", None)
    lines: list[str] = []
    lines.append(f"Name: {lead.first_name} {lead.last_name}".strip())
    if lead.job_title:
        lines.append(f"Title: {lead.job_title}")
    if lead.work_email:
        lines.append(f"Work email: {lead.work_email}")
    elif lead.email:
        lines.append(f"Personal email: {lead.email}")
    if lead.seniority:
        lines.append(f"Seniority: {lead.seniority}")
    if lead.departments:
        lines.append(f"Departments: {lead.departments}")
    if lead.industries:
        lines.append(f"Industries: {lead.industries}")
    if company:
        lines.append(f"Company: {company.company_name}")
        if company.company_city:
            lines.append(f"Location: {company.company_city}")
        if company.technologies:
            lines.append(f"Stack: {company.technologies}")
        if company.employees_amount:
            lines.append(f"Size: {company.employees_amount}")
        if company.latest_funding:
            lines.append(f"Latest funding: {company.latest_funding}")
    if lead.profile_summary:
        lines.append(f"Summary: {_sanitize(lead.profile_summary, 350)}")
    return "\n".join(lines)


def _profile_version(profile: LLMProfile | None) -> str | None:
    if not profile:
        return None
    ts = getattr(profile, "updated_at", None)
    if ts and hasattr(ts, "isoformat"):
        return ts.isoformat()
    return "v1"


def build_chat_messages(
    lead: Lead,
    base_profile: LLMProfile | None,
    cold_overlay: LLMProfile | None,
) -> list[dict[str, str]]:
    context = build_lead_context(lead)
    base_rules = base_profile.rules if base_profile else ""
    overlay_rules = cold_overlay.rules if cold_overlay else ""

    system = (
        "You are an SDR for Kraken Sense writing ultra-personalized, first-touch cold emails. "
        "Stacked guidance:\n"
        f"- Base rules: {base_rules}\n"
        f"- Cold outbound overlay: {overlay_rules}\n"
        "Always personalize to the exact person using lead/company fields provided. "
        "If you have browsing, do a quick scan for recent company/person news (last 90 days); "
        "if not, stay anchored to provided context. Never invent facts."
    )

    user = (
        "Write a 2-3 sentence cold email with NO subject line. "
        "Format strictly:\n"
        "Greeting\n"
        "<2-3 short sentences>\n"
        "Copper\n"
        "Sales Development Representative\n"
        "Kraken Sense\n\n"
        "Rules:\n"
        "- No hyphens or em dashes. No emojis, fluff, or jargon.\n"
        "- Reference the person's role, responsibilities, org context, and any recent (real) news if naturally helpful.\n"
        "- Mention value: faster pathogen detection, reduced lab dependency, easier compliance reporting, early outbreak detection, operational reliability.\n"
        "- Ask briefly for a call or chat if they are interested.\n"
        "- If natural, note it is revolutionary for pathogen testing.\n"
        "- Keep it concise, human, respectful of their time.\n\n"
        f"Lead & company context:\n{context}\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _extract_costs_from_json(data) -> list[Decimal]:
    costs: list[Decimal] = []

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if "cost" in k.lower() and isinstance(v, (int, float, str)):
                    try:
                        costs.append(Decimal(str(v)))
                    except Exception:
                        pass
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return costs


def _read_historical_costs_from_file(path: Path) -> list[Decimal]:
    try:
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return _extract_costs_from_json(data)
        if path.suffix.lower() in {".csv", ".tsv"}:
            delimiter = "," if path.suffix.lower() == ".csv" else "\t"
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                costs: list[Decimal] = []
                for row in reader:
                    for k, v in row.items():
                        if k and "cost" in k.lower() and v:
                            try:
                                costs.append(Decimal(str(v)))
                            except Exception:
                                continue
                return costs
    except Exception:
        return []
    return []


def load_historical_costs() -> list[Decimal]:
    costs: list[Decimal] = []
    for base in HISTORICAL_PATHS:
        if not base.exists():
            continue
        for file in base.rglob("*"):
            if file.is_file() and file.suffix.lower() in {".json", ".csv", ".tsv"}:
                costs.extend(_read_historical_costs_from_file(file))
    return costs


async def average_cost(model: str = DEFAULT_MODEL) -> tuple[Decimal, int]:
    db_costs_raw = await FirstEmail.exclude(cost_usd=None).values_list("cost_usd", flat=True)
    db_costs: list[Decimal] = [Decimal(str(c)) for c in db_costs_raw if c is not None]
    source_costs: list[Decimal] = db_costs

    if not source_costs:
        source_costs = load_historical_costs()

    if source_costs:
        total = sum(source_costs)
        avg = (total / Decimal(len(source_costs))).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        return avg, len(source_costs)

    fallback = estimate_cost_from_tokens(
        model,
        DEFAULT_PROMPT_TOKENS,
        DEFAULT_COMPLETION_TOKENS,
    )
    return fallback, 0


def get_openai_client() -> AsyncOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def _get_default_profile(category: str) -> LLMProfile | None:
    profile = (
        await LLMProfile.filter(category=category)
        .order_by("-is_default", "-updated_at")
        .first()
    )
    if profile:
        return profile

    # Fallback seeding if campaign seeding has not run yet.
    seeds = {
        "general": {
            "name": "Base LLM Rules",
            "description": "Default outreach rules",
            "rules": (
                "Keep emails concise, friendly, and specific to the lead. Do not fabricate facts. Respect opt-outs. "
                "Offer two time windows when proposing meetings. Keep cold emails <= 120 words."
            ),
        },
        "cold_outbound": {
            "name": "Cold Outbound Overlay",
            "description": "Extra rules for cold outbound personalization layered on top of the base profile.",
            "rules": (
                "2-3 sentences, no subject line, greeting + body + Copper / Sales Development Representative / Kraken Sense signoff. "
                "No hyphens or em dashes. No fluff or emojis. Personalize using role/org context and recent news if available. "
                "Highlight pathogen detection value, reduced lab dependency, compliance, early detection, reliability. Brief CTA."
            ),
        },
    }
    seed = seeds.get(category)
    if not seed:
        return None
    created = await LLMProfile.create(
        name=seed["name"],
        description=seed.get("description"),
        rules=seed["rules"],
        category=category,
        is_default=True,
    )
    return created


async def generate_and_store_email(
    lead: Lead,
    user: User | None,
    client: AsyncOpenAI,
    model: str = DEFAULT_MODEL,
    base_profile: LLMProfile | None = None,
    overlay_profile: LLMProfile | None = None,
) -> tuple[FirstEmail, Decimal | None]:
    base_profile = base_profile or await _get_default_profile("general")
    overlay_profile = overlay_profile or await _get_default_profile("cold_outbound")
    messages = build_chat_messages(lead, base_profile, overlay_profile)
    completion = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        max_tokens=320,
    )
    email_text = (completion.choices[0].message.content or "").strip()
    if not email_text:
        raise ValueError("Empty response from model")

    usage = completion.usage
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or prompt_tokens + completion_tokens)

    cost: Decimal | None = None
    if prompt_tokens or completion_tokens:
        cost = estimate_cost_from_tokens(model, prompt_tokens, completion_tokens)

    base_version = _profile_version(base_profile)
    overlay_version = _profile_version(overlay_profile)

    record = await FirstEmail.create(
        lead=lead,
        first_email=email_text,
        approval=False,
        model=model,
        prompt_tokens=prompt_tokens or None,
        completion_tokens=completion_tokens or None,
        total_tokens=total_tokens or None,
        cost_usd=cost,
        created_by=user,
        updated_by=user,
        llm_profile_version=base_version,
        llm_profile_name=base_profile.name if base_profile else None,
        llm_profile_rules=base_profile.rules if base_profile else None,
        llm_overlay_profile_version=overlay_version,
        llm_overlay_profile_name=overlay_profile.name if overlay_profile else None,
        llm_overlay_profile_rules=overlay_profile.rules if overlay_profile else None,
    )
    return record, cost


async def leads_pending_first_email(limit: int | None = None) -> list[Lead]:
    qs = Lead.filter(first_email__isnull=True).order_by("id").prefetch_related("company")
    if limit:
        qs = qs.limit(limit)
    return await qs
