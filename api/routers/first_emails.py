from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.authenticate import authenticate
from models import FirstEmail, Lead, User
from services.email_generation import (
    DEFAULT_MODEL,
    average_cost,
    generate_and_store_email,
    get_openai_client,
    leads_pending_first_email,
)

router = APIRouter(prefix="/first-emails", tags=["first-emails"])


class EmailStats(BaseModel):
    pending: int
    generated: int
    average_cost_usd: float
    estimated_total_cost_usd: float
    model: str
    sample_size: int


class GenerateRequest(BaseModel):
    count: Optional[int] = Field(
        None,
        ge=1,
        le=500,
        description="How many leads to generate emails for (omit to use all pending).",
    )


class GenerateResult(BaseModel):
    attempted: int
    generated: int
    pending_after: int
    total_cost_usd: Optional[float]
    model: str
    errors: list[str] = Field(default_factory=list)


@router.get("/stats", response_model=EmailStats)
async def get_first_email_stats(user: User = Depends(authenticate)):
    pending = await Lead.filter(first_email__isnull=True).count()
    generated = await FirstEmail.all().count()
    avg_cost, sample_size = await average_cost(DEFAULT_MODEL)
    estimated_total = Decimal(pending) * avg_cost
    return EmailStats(
        pending=pending,
        generated=generated,
        average_cost_usd=float(avg_cost),
        estimated_total_cost_usd=float(estimated_total),
        model=DEFAULT_MODEL,
        sample_size=sample_size,
    )


@router.post("/generate", response_model=GenerateResult)
async def generate_first_emails(payload: GenerateRequest, user: User = Depends(authenticate)):
    pending_count = await Lead.filter(first_email__isnull=True).count()
    if pending_count == 0:
        return GenerateResult(
            attempted=0,
            generated=0,
            pending_after=0,
            total_cost_usd=0.0,
            model=DEFAULT_MODEL,
            errors=["No leads need emails."],
        )

    target = payload.count or pending_count
    target = min(target, pending_count)
    client = get_openai_client()

    leads = await leads_pending_first_email(target)
    errors: list[str] = []
    total_cost = Decimal("0")
    generated = 0

    for lead in leads:
        try:
            record, cost = await generate_and_store_email(lead, user, client, DEFAULT_MODEL)
            generated += 1 if record else 0
            if cost is not None:
                total_cost += cost
        except HTTPException:
            raise
        except Exception as e:
            errors.append(f"Lead {lead.id}: {e}")

    pending_after = await Lead.filter(first_email__isnull=True).count()

    return GenerateResult(
        attempted=target,
        generated=generated,
        pending_after=pending_after,
        total_cost_usd=float(total_cost) if generated else None,
        model=DEFAULT_MODEL,
        errors=errors,
    )
