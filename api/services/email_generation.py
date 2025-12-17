from __future__ import annotations

import csv
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Sequence

from fastapi import HTTPException
from openai import AsyncOpenAI

from models import Company, FirstEmail, Lead, User

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_PROMPT_TOKENS = 360
DEFAULT_COMPLETION_TOKENS = 240

MODEL_PRICING: dict[str, dict[str, Decimal]] = {
    # Prices per 1K tokens (USD) — adjust if you change models
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
        return value[: max_length - 1] + "…"
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
        if company.technologies:
            lines.append(f"Stack: {company.technologies}")
        if company.employees_amount:
            lines.append(f"Size: {company.employees_amount}")
    if lead.profile_summary:
        lines.append(f"Summary: {_sanitize(lead.profile_summary, 350)}")
    return "\n".join(lines)


def build_chat_messages(lead: Lead) -> list[dict[str, str]]:
    context = build_lead_context(lead)
    system = (
        "You are an SDR who writes concise, respectful first-touch cold emails. "
        "Personalize each email using the provided lead and company context. "
        "Keep the body under 140 words, avoid exaggeration, and end with a single, low-friction CTA."
    )
    user = (
        "Write an outbound email (subject + body) for this lead. "
        "Use plain text (no HTML) and avoid placeholders. "
        "Ensure the copy feels human and specific to the lead.\n\n"
        f"Lead & company context:\n{context}\n\n"
        "Format:\n"
        "Subject: <compelling subject line>\n"
        "Body:\n"
        "<2-4 short paragraphs with a single CTA>\n"
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


async def generate_and_store_email(
    lead: Lead,
    user: User,
    client: AsyncOpenAI,
    model: str = DEFAULT_MODEL,
) -> tuple[FirstEmail, Decimal | None]:
    messages = build_chat_messages(lead)
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
    )
    return record, cost


async def leads_pending_first_email(limit: int | None = None) -> list[Lead]:
    qs = Lead.filter(first_email__isnull=True).order_by("id").prefetch_related("company")
    if limit:
        qs = qs.limit(limit)
    return await qs
