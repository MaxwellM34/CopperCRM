from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from tortoise.expressions import Q
from auth.authenticate import authenticate
from models import Campaign, FirstEmail, FirstEmailApproval, Lead, User
from services.email_generation import (
    DEFAULT_MODEL,
    average_cost,
    generate_and_store_email,
    get_openai_client,
    leads_pending_first_email,
)

router = APIRouter(prefix="/first-emails", tags=["first-emails"])


class EmailStats(BaseModel):
    pending_to_generate: int
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
    campaign_id: Optional[int] = Field(
        None,
        description="Optional campaign to select LLM profiles for generation.",
    )


class GenerateResult(BaseModel):
    attempted: int
    generated: int
    pending_after: int
    total_cost_usd: Optional[float]
    model: str
    errors: list[str] = Field(default_factory=list)


class PendingEmail(BaseModel):
    id: int
    first_email: str
    created_at: str | None = None
    lead_name: str | None = None
    lead_first_name: str | None = None
    lead_last_name: str | None = None
    lead_email: str | None = None
    lead_work_email: str | None = None
    lead_title: str | None = None
    company_name: str | None = None
    human_approval: bool | None = None
    human_reviewed: bool | None = None


@router.get("/stats", response_model=EmailStats)
async def get_first_email_stats(user: User = Depends(authenticate)):
    pending = await Lead.filter(first_email__isnull=True).count()
    generated = await FirstEmail.all().count()
    avg_cost, sample_size = await average_cost(DEFAULT_MODEL)
    estimated_total = Decimal(pending) * avg_cost
    return EmailStats(
        pending_to_generate=pending,
        generated=generated,
        average_cost_usd=float(avg_cost),
        estimated_total_cost_usd=float(estimated_total),
        model=DEFAULT_MODEL,
        sample_size=sample_size,
    )


@router.post("/generate", response_model=GenerateResult)
async def generate_first_emails(payload: GenerateRequest, user: User = Depends(authenticate)):
    campaign = None
    if payload.campaign_id is not None:
        campaign = (
            await Campaign.filter(id=payload.campaign_id)
            .prefetch_related("llm_profile", "llm_overlay_profile")
            .first()
        )
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found")

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
            record, cost = await generate_and_store_email(
                lead,
                None,
                client,
                DEFAULT_MODEL,
                base_profile=getattr(campaign, "llm_profile", None) if campaign else None,
                overlay_profile=getattr(campaign, "llm_overlay_profile", None) if campaign else None,
            )
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


@router.get("/next", response_model=PendingEmail | dict)
async def get_next_email_for_human_review(user: User = Depends(authenticate)):
    email = (
        await FirstEmail.filter(
            Q(approval_record__human_reviewed=False) | Q(approval_record=None)
        )
        .prefetch_related("lead__company", "approval_record")
        .order_by("-created_at")
        .first()
    )
    if not email:
        return {"status": "no_pending"}

    lead = getattr(email, "lead", None)
    company = getattr(lead, "company", None) if lead else None
    approval = getattr(email, "approval_record", None)

    return PendingEmail(
        id=email.id, #type: ignore
        first_email=email.first_email, #type: ignore
        created_at=email.created_at.isoformat() if email.created_at else None, #type: ignore
        lead_name=f"{lead.first_name} {lead.last_name}".strip() if lead else None,
        lead_first_name=lead.first_name if lead else None,
        lead_last_name=lead.last_name if lead else None,
        lead_email=lead.email if lead else None,
        lead_work_email=lead.work_email if lead else None,
        lead_title=lead.job_title if lead else None,
        company_name=company.company_name if company else None,
        human_approval=approval.human_approval if approval else None,
        human_reviewed=approval.human_reviewed if approval else None,
    )


class DecisionRequest(BaseModel):
    id: int
    decision: str


@router.post("/decision", response_model=dict)
async def set_human_decision(payload: DecisionRequest, user: User = Depends(authenticate)):
    if payload.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")

    email = await FirstEmail.filter(id=payload.id).prefetch_related("approval_record").first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    approval = await FirstEmailApproval.get_or_none(first_email=email)
    if approval is None:
        await FirstEmailApproval.create(
            first_email=email,
            human_approval=(payload.decision == "approved"),
            overall_approval=(payload.decision == "approved"),
            human_reviewed=True,
        )
    else:
        approval.human_approval = payload.decision == "approved" #type: ignore
        approval.overall_approval = payload.decision == "approved" #type: ignore
        approval.human_reviewed = True #type: ignore
        await approval.save()

    return {"status": "ok", "id": email.id, "decision": payload.decision}
