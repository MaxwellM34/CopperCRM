import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth.authenticate import authenticate
from models import Campaign, CampaignEmailDraft, Lead, LeadCampaignState, User
from services.campaign_runtime import enroll_leads_for_campaign, run_campaign_tick, send_draft_email
from services.tracking import build_unsubscribe_token, build_unsubscribe_url

router = APIRouter(prefix="/campaign-runtime", tags=["campaign-runtime"])


def _cron_allowed(request: Request) -> bool:
    secret = os.getenv("CRON_SECRET")
    if not secret:
        return True
    provided = request.headers.get("X-Cron-Secret") or request.query_params.get("cron_secret")
    return provided == secret


class TickRequest(BaseModel):
    campaign_id: int | None = None


class TickResponse(BaseModel):
    campaigns: int
    enrolled: int
    processed: int
    replies: int


@router.post("/tick", response_model=TickResponse)
async def tick_campaigns(payload: TickRequest, request: Request):
    if not _cron_allowed(request):
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    result = await run_campaign_tick(payload.campaign_id)
    return TickResponse(**result)


class EnrollRequest(BaseModel):
    campaign_id: int


class EnrollResponse(BaseModel):
    enrolled: int


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_campaign(payload: EnrollRequest, user: User = Depends(authenticate)):
    campaign = await Campaign.filter(id=payload.campaign_id).first()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    enrolled = await enroll_leads_for_campaign(campaign)
    return EnrollResponse(enrolled=enrolled)


class CampaignDraftPreview(BaseModel):
    id: int
    subject: str | None
    body_text: str
    body_html: str | None
    created_at: str | None
    campaign_name: str | None
    step_title: str | None
    from_email: str | None
    to_email: str | None
    lead_name: str | None
    lead_title: str | None
    company_name: str | None
    unsubscribe_url: str | None


@router.get("/drafts/next", response_model=CampaignDraftPreview | dict)
async def get_next_campaign_draft(user: User = Depends(authenticate)):
    draft = (
        await CampaignEmailDraft.filter(status="pending")
        .prefetch_related("lead__company", "campaign", "inbox", "step")
        .order_by("created_at")
        .first()
    )
    if not draft:
        return {"status": "no_pending"}

    lead = getattr(draft, "lead", None)
    company = getattr(lead, "company", None) if lead else None
    campaign = getattr(draft, "campaign", None)
    step = getattr(draft, "step", None)
    lead_name = f"{lead.first_name} {lead.last_name}".strip() if lead else None
    lead_email = lead.work_email or lead.email if lead else None
    token = build_unsubscribe_token(lead.id, lead_email) if lead else None
    unsubscribe_url = build_unsubscribe_url(token) if token else None

    return CampaignDraftPreview(
        id=draft.id,  # type: ignore[arg-type]
        subject=draft.subject,
        body_text=draft.body_text,
        body_html=draft.body_html,
        created_at=draft.created_at.isoformat() if draft.created_at else None,  # type: ignore[arg-type]
        campaign_name=campaign.name if campaign else None,
        step_title=step.title if step else None,
        from_email=draft.from_email or (draft.inbox.email_address if draft.inbox else None),
        to_email=draft.to_email or lead_email,
        lead_name=lead_name,
        lead_title=lead.job_title if lead else None,
        company_name=company.company_name if company else None,
        unsubscribe_url=unsubscribe_url,
    )


class DraftDecisionRequest(BaseModel):
    id: int
    decision: str


@router.post("/drafts/decision", response_model=dict)
async def decide_campaign_draft(payload: DraftDecisionRequest, user: User = Depends(authenticate)):
    if payload.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")

    draft = (
        await CampaignEmailDraft.filter(id=payload.id)
        .prefetch_related("lead", "campaign", "inbox", "step")
        .first()
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if payload.decision == "rejected":
        draft.status = "rejected"  # type: ignore[assignment]
        draft.approved_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        draft.approved_by = user  # type: ignore[assignment]
        await draft.save()
        state = await LeadCampaignState.filter(lead=draft.lead, campaign=draft.campaign).first()
        if state:
            state.status = "stopped"  # type: ignore[assignment]
            await state.save()
        return {"status": "ok", "id": draft.id, "decision": payload.decision}

    await send_draft_email(draft=draft, user=user)
    return {"status": "ok", "id": draft.id, "decision": payload.decision}


class DraftStats(BaseModel):
    pending: int


@router.get("/drafts/stats", response_model=DraftStats)
async def get_draft_stats(user: User = Depends(authenticate)):
    pending = await CampaignEmailDraft.filter(status="pending").count()
    return DraftStats(pending=pending)
