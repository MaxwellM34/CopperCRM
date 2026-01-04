from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.authenticate import authenticate
from models import Campaign, CampaignStep, CampaignEdge, LLMProfile, User

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


BASE_LLM_PROFILE = {
    "name": "Base LLM Rules",
    "description": "Default context about the company, tone, and guardrails used across campaigns.",
    "rules": (
        "You are the Copper CRM outreach AI. Keep messages concise, friendly, and specific to the lead's role. "
        "Never fabricate data. Use provided lead/company context only. Respect unsubscribe or negative signals and "
        "stop immediately. Offer meetings with 2 time windows when appropriate. Avoid jargon, keep to 120 words max "
        "for cold emails, and answer questions directly before re-proposing a call if interest is detected."
    ),
    "category": "general",
}

COLD_OUTBOUND_OVERLAY_PROFILE = {
    "name": "Cold Outbound Overlay",
    "description": "Extra rules for cold outbound personalization layered on top of the base profile.",
    "rules": (
        "Write short (2-3 sentence) cold emails with no subject line. Start with a greeting, end with the exact signoff "
        "lines: 'Copper' on one line, 'Sales Development Representative' on the next, 'Kraken Sense' on the next. "
        "No hyphens or em dashes. Avoid fluff, jargon, emojis. Personalize using role, org context, and any recent "
        "news if available; otherwise stick to provided data. Mention benefits: faster pathogen detection, reduced lab "
        "dependency, easier compliance reporting, early outbreak detection, operational reliability. Ask briefly for a call/chat. "
        "If natural, note that the approach is revolutionary for pathogen testing."
    ),
    "category": "cold_outbound",
}


DRIP_PRESET = {
    "key": "ai_cold_outbound_drip",
    "name": "AI Cold Outbound Drip",
    "description": "Branched cold sequence with AI follow ups, reply handling, and outcomes.",
    "entry_point": "Cold outbound leads imported from CSV or enrichment.",
    "ai_brief": (
        "Use AI to write every touch with the lead and company context. When a prospect replies with a "
        "question but no meeting yet, answer directly, keep the thread going, and propose a call after one "
        "or two exchanges. Stop immediately on unsubscribe or negative sentiment."
    ),
    "audience_size": 120,
    "steps": [
        {
            "title": "Audience: cold leads",
            "step_type": "entry",
            "lane": "Source",
            "sequence": 1,
            "config": {
                "source": "CSV import or intent feed",
                "compliance": "Honor do-not-contact flags and skip replies automatically.",
            },
            "prompt_template": "Take inbound leads from CSV or enrichment. Respect opt-outs and hard bounces.",
            "position_x": 0,
            "position_y": 0,
        },
        {
            "title": "AI email #1 (opener)",
            "step_type": "ai_email",
            "lane": "Touches",
            "sequence": 2,
            "config": {
                "tone": "curious and concise",
                "cta": "Suggest a quick intro call with two time windows",
                "ai_model": "gpt-4o-mini",
                "personalization": "Use role, industry, and recent signals if present.",
                "reply_wait_hours": 48,
            },
            "prompt_template": (
                "Write a concise opener (<=110 words) using lead/company details. "
                "Share a single value prop and propose two meeting windows."
            ),
            "position_x": 220,
            "position_y": 0,
        },
        {
            "title": "Open email #1?",
            "step_type": "condition",
            "lane": "Decisions",
            "sequence": 3,
            "config": {"event": "email_open", "window_hours": 48},
            "prompt_template": "Check if the lead opened email #1 within 2 days.",
            "position_x": 440,
            "position_y": -120,
        },
        {
            "title": "Add +10 points",
            "step_type": "points",
            "lane": "Scoring",
            "sequence": 4,
            "config": {"points": 10, "reason": "Opened email #1"},
            "prompt_template": "Award points for opening the first email.",
            "position_x": 640,
            "position_y": -220,
        },
        {
            "title": "Wait 2 days",
            "step_type": "delay",
            "lane": "Timing",
            "sequence": 5,
            "config": {"duration_hours": 48, "respect_work_hours": True},
            "prompt_template": "Delay send by ~48h and avoid weekend/overnight windows.",
            "position_x": 640,
            "position_y": 0,
        },
        {
            "title": "AI follow-up #2",
            "step_type": "ai_email",
            "lane": "Touches",
            "sequence": 6,
            "config": {
                "tone": "direct but friendly",
                "cta": "Share 1-line value prop plus a soft ask for a call",
                "ai_model": "gpt-4o-mini",
                "variant": "Short proof point followed by a question.",
                "reply_wait_hours": 72,
            },
            "prompt_template": (
                "Write a follow-up that adds one proof point. Ask a short question to elicit a reply and keep "
                "a soft CTA for a call."
            ),
            "position_x": 840,
            "position_y": 0,
        },
        {
            "title": "Wait 3 days",
            "step_type": "delay",
            "lane": "Timing",
            "sequence": 7,
            "config": {"duration_hours": 72, "respect_work_hours": True},
            "prompt_template": "Delay send by ~72h and avoid weekend/overnight windows.",
            "position_x": 1040,
            "position_y": 0,
        },
        {
            "title": "AI follow-up #3",
            "step_type": "ai_email",
            "lane": "Touches",
            "sequence": 8,
            "config": {
                "tone": "helpful and consultative",
                "cta": "Offer to answer a quick question and propose a meeting",
                "ai_model": "gpt-4o-mini",
                "variant": "Share a short case insight to reopen the thread.",
                "reply_wait_hours": 96,
            },
            "prompt_template": (
                "Write a concise, helpful follow-up with one short case insight. "
                "Invite a question, then propose a call if interest is shown."
            ),
            "position_x": 1240,
            "position_y": 0,
        },
        {
            "title": "AI reply handling",
            "step_type": "ai_decision",
            "lane": "Logic",
            "sequence": 9,
            "config": {
                "model": "gpt-4o-mini",
                "routing": [
                    {
                        "if": "Reply mentions scheduling or shares availability.",
                        "then": "Send booking link, confirm time, mark success.",
                    },
                    {
                        "if": "Reply asks a question but does not accept a meeting yet.",
                        "then": "AI answers the question, keeps tone concise, and offers a call after one follow-up.",
                    },
                    {"if": "Negative or unsubscribe intent.", "then": "Stop sequence and mark do_not_contact."},
                ],
                "auto_continue": True,
                "handoff_after": 2,
            },
            "prompt_template": (
                "Read the latest reply. If they propose a time or ask for a booking link, confirm and send it. "
                "If they ask a question but do not accept a meeting yet, answer directly and keep the thread going, "
                "then offer a call. If negative or unsubscribe, stop immediately."
            ),
            "position_x": 900,
            "position_y": -240,
        },
        {
            "title": "Add +50 points",
            "step_type": "points",
            "lane": "Scoring",
            "sequence": 10,
            "config": {"points": 50, "reason": "Meeting request"},
            "prompt_template": "Award points when a meeting is requested.",
            "position_x": 1080,
            "position_y": -360,
        },
        {
            "title": "AI answer question",
            "step_type": "ai_email",
            "lane": "Touches",
            "sequence": 11,
            "config": {
                "tone": "helpful and precise",
                "cta": "Answer the question, then invite a short call if it helps",
                "ai_model": "gpt-4o-mini",
                "reply_mode": True,
            },
            "prompt_template": (
                "Answer the question directly using the thread context. Keep it short and useful, then ask if they "
                "are open to a quick call."
            ),
            "position_x": 1080,
            "position_y": -180,
        },
        {
            "title": "Wait 2 days (post reply)",
            "step_type": "delay",
            "lane": "Timing",
            "sequence": 12,
            "config": {"duration_hours": 48, "respect_work_hours": True},
            "prompt_template": "Wait for a response after answering their question.",
            "position_x": 1260,
            "position_y": -180,
        },
        {
            "title": "Book meeting",
            "step_type": "goal",
            "lane": "Outcomes",
            "sequence": 13,
            "config": {
                "action": "Drop calendar link and set status to meeting_scheduled",
                "handoff": "Notify human owner on first confirmed slot.",
            },
            "prompt_template": "Mark success when a meeting is confirmed; notify the human owner.",
            "position_x": 1260,
            "position_y": -360,
        },
        {
            "title": "Nurture or stop",
            "step_type": "exit",
            "lane": "Outcomes",
            "sequence": 14,
            "config": {
                "action": "Move to nurture list if warm, otherwise stop outreach.",
                "notes": "Stop entirely after auto-reply detected twice.",
            },
            "prompt_template": "If not booked, move warm leads to nurture; stop for cold/negative leads.",
            "position_x": 1260,
            "position_y": 140,
        },
    ],
    "edges": [
        {"from_sequence": 1, "to_sequence": 2, "condition_type": "always", "label": "Start"},
        {"from_sequence": 2, "to_sequence": 3, "condition_type": "no_reply", "label": "No reply"},
        {"from_sequence": 2, "to_sequence": 9, "condition_type": "reply", "label": "Reply"},
        {"from_sequence": 3, "to_sequence": 4, "condition_type": "open", "label": "Opened"},
        {"from_sequence": 3, "to_sequence": 5, "condition_type": "no_open", "label": "No open"},
        {"from_sequence": 4, "to_sequence": 5, "condition_type": "always", "label": "Scored"},
        {"from_sequence": 5, "to_sequence": 6, "condition_type": "always", "label": "Delay done"},
        {"from_sequence": 6, "to_sequence": 9, "condition_type": "reply", "label": "Reply"},
        {"from_sequence": 6, "to_sequence": 7, "condition_type": "no_reply", "label": "No reply"},
        {"from_sequence": 7, "to_sequence": 8, "condition_type": "always", "label": "Delay done"},
        {"from_sequence": 8, "to_sequence": 9, "condition_type": "reply", "label": "Reply"},
        {"from_sequence": 8, "to_sequence": 14, "condition_type": "no_reply", "label": "No reply"},
        {"from_sequence": 9, "to_sequence": 10, "condition_type": "intent", "condition_value": "meeting_request", "label": "Meeting"},
        {"from_sequence": 10, "to_sequence": 13, "condition_type": "always", "label": "Scored"},
        {"from_sequence": 9, "to_sequence": 11, "condition_type": "intent", "condition_value": "question", "label": "Question"},
        {"from_sequence": 9, "to_sequence": 14, "condition_type": "intent", "condition_value": "negative", "label": "Negative"},
        {"from_sequence": 9, "to_sequence": 14, "condition_type": "intent", "condition_value": "unsubscribe", "label": "Unsubscribe"},
        {"from_sequence": 9, "to_sequence": 14, "condition_type": "intent", "condition_value": "no_interest", "label": "No interest"},
        {"from_sequence": 9, "to_sequence": 14, "condition_type": "always", "label": "Default"},
        {"from_sequence": 11, "to_sequence": 9, "condition_type": "reply", "label": "Reply"},
        {"from_sequence": 11, "to_sequence": 12, "condition_type": "no_reply", "label": "No reply"},
        {"from_sequence": 12, "to_sequence": 9, "condition_type": "reply", "label": "Reply"},
        {"from_sequence": 12, "to_sequence": 14, "condition_type": "always", "label": "Timeout"},
    ],
}


class LLMProfilePayload(BaseModel):
    name: str
    rules: str
    description: str | None = None
    category: str = "general"
    is_default: bool | None = None


class LLMProfileResponse(BaseModel):
    id: int
    name: str
    description: str | None
    rules: str
    category: str
    is_default: bool
    created_at: str | None = None
    updated_at: str | None = None


class CampaignStepPayload(BaseModel):
    id: int | None = None
    client_id: str | None = None
    title: str
    step_type: str
    sequence: int = 1
    lane: str | None = None
    position_x: int | None = None
    position_y: int | None = None
    prompt_template: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class CampaignEdgePayload(BaseModel):
    id: int | None = None
    from_step_id: int | None = None
    to_step_id: int | None = None
    from_client_id: str | None = None
    to_client_id: str | None = None
    condition_type: str = "always"
    condition_value: str | None = None
    label: str | None = None
    order: int = 1


class CampaignPayload(BaseModel):
    name: str
    description: str | None = None
    category: str = "cold_outbound"
    status: str = "draft"
    preset_key: str | None = None
    audience_size: int | None = None
    entry_point: str | None = None
    ai_brief: str | None = None
    launch_notes: str | None = None
    llm_profile_id: int | None = None
    llm_overlay_profile_id: int | None = None
    steps: list[CampaignStepPayload] = Field(default_factory=list)
    edges: list[CampaignEdgePayload] = Field(default_factory=list)


class LaunchRequest(BaseModel):
    notes: str | None = None
    audience_size: int | None = None


class CampaignStepResponse(BaseModel):
    id: int
    client_id: str | None = None
    title: str
    step_type: str
    sequence: int = 1
    lane: str | None = None
    position_x: int | None = None
    position_y: int | None = None
    prompt_template: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class CampaignEdgeResponse(BaseModel):
    id: int
    from_step_id: int
    to_step_id: int
    condition_type: str
    condition_value: str | None = None
    label: str | None = None
    order: int = 1
    created_at: str | None = None
    updated_at: str | None = None


class CampaignSummary(BaseModel):
    id: int
    name: str
    description: str | None
    category: str
    status: str
    preset_key: str | None
    audience_size: int | None
    entry_point: str | None
    ai_brief: str | None
    launch_notes: str | None
    launched_at: str | None
    llm_profile_id: int | None = None
    llm_profile_name: str | None = None
    llm_overlay_profile_id: int | None = None
    llm_overlay_profile_name: str | None = None
    created_at: str | None
    updated_at: str | None
    step_count: int = 0


class CampaignDetail(CampaignSummary):
    steps: list[CampaignStepResponse] = Field(default_factory=list)
    edges: list[CampaignEdgeResponse] = Field(default_factory=list)


def _iso_or_none(value: Any) -> str | None:
    iso: Callable[[], str] | None = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return None


async def _ensure_default_llm_profile(user: User) -> LLMProfile:
    profile = (
        await LLMProfile.filter(is_default=True, category="general")
        .order_by("-updated_at")
        .first()
    )
    if profile:
        return profile

    profile = await LLMProfile.filter(name=BASE_LLM_PROFILE["name"], category="general").first()
    if profile:
        profile.is_default = True  # type: ignore[assignment]
        await profile.save()
        return profile

    return await LLMProfile.create(
        name=BASE_LLM_PROFILE["name"],
        description=BASE_LLM_PROFILE["description"],
        rules=BASE_LLM_PROFILE["rules"],
        category=BASE_LLM_PROFILE["category"],
        is_default=True,
    )


async def _ensure_default_cold_outbound_profile() -> LLMProfile:
    profile = (
        await LLMProfile.filter(is_default=True, category="cold_outbound")
        .order_by("-updated_at")
        .first()
    )
    if profile:
        return profile

    existing = await LLMProfile.filter(
        name=COLD_OUTBOUND_OVERLAY_PROFILE["name"], category="cold_outbound"
    ).first()
    if existing:
        if not existing.is_default:
            existing.is_default = True  # type: ignore[assignment]
            await existing.save()
        return existing

    return await LLMProfile.create(
        name=COLD_OUTBOUND_OVERLAY_PROFILE["name"],
        description=COLD_OUTBOUND_OVERLAY_PROFILE["description"],
        rules=COLD_OUTBOUND_OVERLAY_PROFILE["rules"],
        category=COLD_OUTBOUND_OVERLAY_PROFILE["category"],
        is_default=True,
    )


async def _seed_preset_edges(campaign: Campaign, steps: list[CampaignStep]) -> None:
    edges = DRIP_PRESET.get("edges") or []
    if not edges:
        return
    step_map = {step.sequence: step for step in steps}
    for idx, edge in enumerate(edges, start=1):
        from_step = step_map.get(edge.get("from_sequence"))
        to_step = step_map.get(edge.get("to_sequence"))
        if not from_step or not to_step:
            continue
        await CampaignEdge.create(
            campaign=campaign,
            from_step=from_step,
            to_step=to_step,
            condition_type=edge.get("condition_type") or "always",
            condition_value=edge.get("condition_value"),
            label=edge.get("label"),
            order=edge.get("order") or idx,
        )


async def _seed_default_campaign(user: User) -> Campaign:
    default_profile = await _ensure_default_llm_profile(user)
    overlay_profile = await _ensure_default_cold_outbound_profile()
    existing = (
        await Campaign.filter(preset_key=DRIP_PRESET["key"])
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .first()
    )
    if existing:
        needs_save = False
        if existing.llm_profile is None:
            existing.llm_profile = default_profile  # type: ignore[assignment]
            needs_save = True
        if existing.llm_overlay_profile is None and existing.category == "cold_outbound":
            existing.llm_overlay_profile = overlay_profile  # type: ignore[assignment]
            needs_save = True
        if needs_save:
            await existing.save()
        if not (getattr(existing, "edges", []) or []):
            steps = getattr(existing, "steps", []) or []
            await _seed_preset_edges(existing, steps)
            refreshed = (
                await Campaign.filter(id=existing.id)
                .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
                .first()
            )
            if refreshed:
                return refreshed
        return existing

    campaign = await Campaign.create(
        name=DRIP_PRESET["name"],
        description=DRIP_PRESET["description"],
        category="cold_outbound",
        status="draft",
        preset_key=DRIP_PRESET["key"],
        entry_point=DRIP_PRESET["entry_point"],
        ai_brief=DRIP_PRESET["ai_brief"],
        audience_size=DRIP_PRESET["audience_size"],
        created_by=user,
        updated_by=user,
        llm_profile=default_profile,
        llm_overlay_profile=overlay_profile,
    )

    for idx, step in enumerate(DRIP_PRESET["steps"], start=1):
        await CampaignStep.create(
            campaign=campaign,
            title=step["title"],
            step_type=step["step_type"],
            sequence=step.get("sequence", idx),
            lane=step.get("lane"),
            prompt_template=step.get("prompt_template"),
            config=step.get("config") or {},
            position_x=step.get("position_x"),
            position_y=step.get("position_y"),
        )

    steps = await CampaignStep.filter(campaign=campaign).all()
    await _seed_preset_edges(campaign, steps)

    created = (
        await Campaign.filter(id=campaign.id)
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .first()
    )
    return created or campaign


def _serialize_step(step: CampaignStep) -> CampaignStepResponse:
    return CampaignStepResponse(
        id=step.id,  # type: ignore[arg-type]
        client_id=None,
        title=step.title,  # type: ignore[arg-type]
        step_type=step.step_type,  # type: ignore[arg-type]
        sequence=step.sequence,  # type: ignore[arg-type]
        lane=step.lane,  # type: ignore[arg-type]
        config=step.config or {},  # type: ignore[arg-type]
        prompt_template=getattr(step, "prompt_template", None),
        position_x=step.position_x,  # type: ignore[arg-type]
        position_y=step.position_y,  # type: ignore[arg-type]
        created_at=_iso_or_none(getattr(step, "created_at", None)),
        updated_at=_iso_or_none(getattr(step, "updated_at", None)),
    )


def _serialize_edge(edge: CampaignEdge) -> CampaignEdgeResponse:
    return CampaignEdgeResponse(
        id=edge.id,  # type: ignore[arg-type]
        from_step_id=edge.from_step_id,  # type: ignore[arg-type]
        to_step_id=edge.to_step_id,  # type: ignore[arg-type]
        condition_type=edge.condition_type,  # type: ignore[arg-type]
        condition_value=edge.condition_value,  # type: ignore[arg-type]
        label=edge.label,  # type: ignore[arg-type]
        order=edge.order,  # type: ignore[arg-type]
        created_at=_iso_or_none(getattr(edge, "created_at", None)),
        updated_at=_iso_or_none(getattr(edge, "updated_at", None)),
    )


def _serialize_campaign(
    campaign: Campaign,
    include_steps: bool = False,
    step_count: int | None = None,
) -> CampaignDetail | CampaignSummary:
    llm_profile = getattr(campaign, "llm_profile", None)
    llm_overlay_profile = getattr(campaign, "llm_overlay_profile", None)
    base_kwargs: dict[str, Any] = dict(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        category=campaign.category,
        status=campaign.status,
        preset_key=campaign.preset_key,
        audience_size=campaign.audience_size,
        entry_point=campaign.entry_point,
        ai_brief=campaign.ai_brief,
        launch_notes=campaign.launch_notes,
        launched_at=_iso_or_none(getattr(campaign, "launched_at", None)),
        llm_profile_id=llm_profile.id if llm_profile else None,
        llm_profile_name=llm_profile.name if llm_profile else None,
        llm_overlay_profile_id=llm_overlay_profile.id if llm_overlay_profile else None,
        llm_overlay_profile_name=llm_overlay_profile.name if llm_overlay_profile else None,
        created_at=_iso_or_none(getattr(campaign, "created_at", None)),
        updated_at=_iso_or_none(getattr(campaign, "updated_at", None)),
        step_count=step_count if step_count is not None else 0,
    )

    if include_steps:
        steps = getattr(campaign, "steps", []) or []
        sorted_steps = sorted(
            steps,
            key=lambda s: (getattr(s, "sequence", 0) or 0, getattr(s, "id", 0) or 0),
        )
        serialized_steps = [_serialize_step(step) for step in sorted_steps]
        edges = getattr(campaign, "edges", []) or []
        sorted_edges = sorted(
            edges,
            key=lambda e: (getattr(e, "order", 0) or 0, getattr(e, "id", 0) or 0),
        )
        serialized_edges = [_serialize_edge(edge) for edge in sorted_edges]
        base_kwargs["step_count"] = step_count if step_count is not None else len(serialized_steps)
        return CampaignDetail(steps=serialized_steps, edges=serialized_edges, **base_kwargs)

    return CampaignSummary(**base_kwargs)


def _resolve_edge_step_id(
    edge: CampaignEdgePayload,
    client_steps: dict[str, CampaignStep],
    side: str,
) -> int | None:
    if side == "from":
        if edge.from_step_id is not None:
            return edge.from_step_id
        if edge.from_client_id and edge.from_client_id in client_steps:
            return client_steps[edge.from_client_id].id  # type: ignore[return-value]
        return None
    if edge.to_step_id is not None:
        return edge.to_step_id
    if edge.to_client_id and edge.to_client_id in client_steps:
        return client_steps[edge.to_client_id].id  # type: ignore[return-value]
    return None


async def _resolve_profile(
    profile_id: int | None,
    category: str,
    user: User,
) -> LLMProfile | None:
    if profile_id is None:
        if category == "general":
            return await _ensure_default_llm_profile(user)
        if category == "cold_outbound":
            return await _ensure_default_cold_outbound_profile()
        return None

    profile = await LLMProfile.filter(id=profile_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="LLM profile not found")
    if profile.category != category:
        raise HTTPException(
            status_code=400,
            detail=f"LLM profile category mismatch (expected {category})",
        )
    return profile


@router.get("", response_model=list[CampaignSummary])
async def list_campaigns(user: User = Depends(authenticate)):
    await _seed_default_campaign(user)
    campaigns = (
        await Campaign.all()
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .order_by("-updated_at", "-id")
    )
    summaries: list[CampaignSummary] = []
    for campaign in campaigns:
        steps = getattr(campaign, "steps", []) or []
        summaries.append(_serialize_campaign(campaign, include_steps=False, step_count=len(steps)))  # type: ignore[arg-type]
    return summaries


@router.get("/presets/drip", response_model=CampaignDetail)
async def get_drip_preset(user: User = Depends(authenticate)):
    campaign = await _seed_default_campaign(user)
    steps = getattr(campaign, "steps", []) or []
    return _serialize_campaign(campaign, include_steps=True, step_count=len(steps))  # type: ignore[return-value]


@router.get("/llm-profiles", response_model=list[LLMProfileResponse])
async def list_llm_profiles(user: User = Depends(authenticate)):
    await _ensure_default_llm_profile(user)
    await _ensure_default_cold_outbound_profile()
    profiles = await LLMProfile.all().order_by("-is_default", "name")
    return [
        LLMProfileResponse(
            id=p.id,  # type: ignore[arg-type]
            name=p.name,  # type: ignore[arg-type]
            description=p.description,  # type: ignore[arg-type]
            rules=p.rules,  # type: ignore[arg-type]
            category=p.category,  # type: ignore[arg-type]
            is_default=bool(p.is_default),
            created_at=p.created_at.isoformat() if p.created_at else None,  # type: ignore[arg-type]
            updated_at=p.updated_at.isoformat() if p.updated_at else None,  # type: ignore[arg-type]
        )
        for p in profiles
    ]


@router.get("/llm-profiles/default", response_model=LLMProfileResponse)
async def get_default_llm_profile(user: User = Depends(authenticate)):
    profile = await _ensure_default_llm_profile(user)
    return LLMProfileResponse(
        id=profile.id,  # type: ignore[arg-type]
        name=profile.name,  # type: ignore[arg-type]
        description=profile.description,  # type: ignore[arg-type]
        rules=profile.rules,  # type: ignore[arg-type]
        category=profile.category,  # type: ignore[arg-type]
        is_default=bool(profile.is_default),
        created_at=profile.created_at.isoformat() if profile.created_at else None,  # type: ignore[arg-type]
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,  # type: ignore[arg-type]
    )


@router.post("/llm-profiles", response_model=LLMProfileResponse)
async def create_llm_profile(payload: LLMProfilePayload, user: User = Depends(authenticate)):
    is_default = bool(payload.is_default) if payload.is_default is not None else False
    profile = await LLMProfile.create(
        name=payload.name,
        description=payload.description,
        rules=payload.rules,
        category=payload.category or "general",
        is_default=is_default,
    )
    if is_default:
        await LLMProfile.filter(id__not=profile.id, category=profile.category).update(is_default=False)

    return LLMProfileResponse(
        id=profile.id,  # type: ignore[arg-type]
        name=profile.name,  # type: ignore[arg-type]
        description=profile.description,  # type: ignore[arg-type]
        rules=profile.rules,  # type: ignore[arg-type]
        category=profile.category,  # type: ignore[arg-type]
        is_default=bool(profile.is_default),
        created_at=profile.created_at.isoformat() if profile.created_at else None,  # type: ignore[arg-type]
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,  # type: ignore[arg-type]
    )


@router.put("/llm-profiles/{profile_id}", response_model=LLMProfileResponse)
async def update_llm_profile(profile_id: int, payload: LLMProfilePayload, user: User = Depends(authenticate)):
    profile = await LLMProfile.filter(id=profile_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="LLM profile not found")

    profile.name = payload.name  # type: ignore[assignment]
    profile.description = payload.description  # type: ignore[assignment]
    profile.rules = payload.rules  # type: ignore[assignment]
    profile.category = payload.category or profile.category  # type: ignore[assignment]
    if payload.is_default is not None:
        profile.is_default = bool(payload.is_default)  # type: ignore[assignment]
    await profile.save()

    if profile.is_default:
        await LLMProfile.filter(id__not=profile.id, category=profile.category).update(is_default=False)
    else:
        # Ensure at least one default exists for the category
        if profile.category == "cold_outbound":
            await _ensure_default_cold_outbound_profile()
        else:
            await _ensure_default_llm_profile(user)

    return LLMProfileResponse(
        id=profile.id,  # type: ignore[arg-type]
        name=profile.name,  # type: ignore[arg-type]
        description=profile.description,  # type: ignore[arg-type]
        rules=profile.rules,  # type: ignore[arg-type]
        category=profile.category,  # type: ignore[arg-type]
        is_default=bool(profile.is_default),
        created_at=profile.created_at.isoformat() if profile.created_at else None,  # type: ignore[arg-type]
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,  # type: ignore[arg-type]
    )


@router.post("", response_model=CampaignDetail)
async def create_campaign(payload: CampaignPayload, user: User = Depends(authenticate)):
    steps_payload = payload.steps
    use_preset_edges = False
    if not steps_payload and payload.preset_key == DRIP_PRESET["key"]:
        steps_payload = [CampaignStepPayload(**step) for step in DRIP_PRESET["steps"]]
        if not payload.edges:
            use_preset_edges = True

    llm_profile = await _resolve_profile(payload.llm_profile_id, "general", user)
    llm_overlay_profile = None
    if payload.llm_overlay_profile_id is not None:
        llm_overlay_profile = await _resolve_profile(
            payload.llm_overlay_profile_id, "cold_outbound", user
        )
    elif payload.category == "cold_outbound":
        llm_overlay_profile = await _ensure_default_cold_outbound_profile()

    campaign = await Campaign.create(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        status=payload.status or "draft",
        preset_key=payload.preset_key,
        audience_size=payload.audience_size,
        entry_point=payload.entry_point,
        ai_brief=payload.ai_brief,
        launch_notes=payload.launch_notes,
        created_by=user,
        updated_by=user,
        llm_profile=llm_profile,
        llm_overlay_profile=llm_overlay_profile,
    )

    client_steps: dict[str, CampaignStep] = {}
    created_steps: list[CampaignStep] = []
    for idx, step in enumerate(steps_payload, start=1):
        created = await CampaignStep.create(
            campaign=campaign,
            title=step.title,
            step_type=step.step_type,
            sequence=step.sequence or idx,
            lane=step.lane,
            prompt_template=step.prompt_template,
            config=step.config or {},
            position_x=step.position_x,
            position_y=step.position_y,
        )
        created_steps.append(created)
        if step.client_id:
            client_steps[step.client_id] = created

    if payload.edges:
        for idx, edge in enumerate(payload.edges, start=1):
            from_id = _resolve_edge_step_id(edge, client_steps, "from")
            to_id = _resolve_edge_step_id(edge, client_steps, "to")
            if not from_id or not to_id:
                raise HTTPException(
                    status_code=400,
                    detail="Edge references unknown steps. Save steps first or provide client_id mapping.",
                )
            await CampaignEdge.create(
                campaign=campaign,
                from_step_id=from_id,
                to_step_id=to_id,
                condition_type=edge.condition_type,
                condition_value=edge.condition_value,
                label=edge.label,
                order=edge.order or idx,
            )
    elif use_preset_edges:
        await _seed_preset_edges(campaign, created_steps)

    created = (
        await Campaign.filter(id=campaign.id)
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .first()
    )
    if created is None:
        raise HTTPException(status_code=500, detail="Campaign not created")
    steps = getattr(created, "steps", []) or []
    return _serialize_campaign(created, include_steps=True, step_count=len(steps))  # type: ignore[return-value]


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(campaign_id: int, user: User = Depends(authenticate)):
    await _seed_default_campaign(user)
    campaign = (
        await Campaign.filter(id=campaign_id)
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .first()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    steps = getattr(campaign, "steps", []) or []
    return _serialize_campaign(campaign, include_steps=True, step_count=len(steps))  # type: ignore[return-value]


@router.put("/{campaign_id}", response_model=CampaignDetail)
async def update_campaign(
    campaign_id: int, payload: CampaignPayload, user: User = Depends(authenticate)
):
    campaign = (
        await Campaign.filter(id=campaign_id)
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .first()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    llm_profile = await _resolve_profile(payload.llm_profile_id, "general", user)
    llm_overlay_profile = None
    if payload.llm_overlay_profile_id is not None:
        llm_overlay_profile = await _resolve_profile(
            payload.llm_overlay_profile_id, "cold_outbound", user
        )
    elif payload.category == "cold_outbound":
        llm_overlay_profile = await _ensure_default_cold_outbound_profile()

    campaign.name = payload.name  # type: ignore[assignment]
    campaign.description = payload.description  # type: ignore[assignment]
    campaign.category = payload.category  # type: ignore[assignment]
    campaign.status = payload.status or "draft"  # type: ignore[assignment]
    campaign.preset_key = payload.preset_key  # type: ignore[assignment]
    campaign.audience_size = payload.audience_size  # type: ignore[assignment]
    campaign.entry_point = payload.entry_point  # type: ignore[assignment]
    campaign.ai_brief = payload.ai_brief  # type: ignore[assignment]
    campaign.launch_notes = payload.launch_notes  # type: ignore[assignment]
    campaign.llm_profile = llm_profile  # type: ignore[assignment]
    campaign.llm_overlay_profile = llm_overlay_profile  # type: ignore[assignment]
    campaign.updated_by = user  # type: ignore[assignment]
    await campaign.save()

    existing_steps = {step.id: step for step in (getattr(campaign, "steps", []) or [])}
    client_steps: dict[str, CampaignStep] = {}
    kept_ids: set[int] = set()

    for idx, step in enumerate(payload.steps, start=1):
        if step.id is not None and step.id in existing_steps:
            current = existing_steps[step.id]
            current.title = step.title  # type: ignore[assignment]
            current.step_type = step.step_type  # type: ignore[assignment]
            current.sequence = step.sequence or idx  # type: ignore[assignment]
            current.lane = step.lane  # type: ignore[assignment]
            current.prompt_template = step.prompt_template  # type: ignore[assignment]
            current.config = step.config or {}  # type: ignore[assignment]
            current.position_x = step.position_x  # type: ignore[assignment]
            current.position_y = step.position_y  # type: ignore[assignment]
            await current.save()
        else:
            current = await CampaignStep.create(
                campaign=campaign,
                title=step.title,
                step_type=step.step_type,
                sequence=step.sequence or idx,
                lane=step.lane,
                prompt_template=step.prompt_template,
                config=step.config or {},
                position_x=step.position_x,
                position_y=step.position_y,
            )
        kept_ids.add(current.id)  # type: ignore[arg-type]
        if step.client_id:
            client_steps[step.client_id] = current

    if kept_ids:
        await CampaignStep.filter(campaign=campaign).exclude(id__in=list(kept_ids)).delete()
    else:
        await CampaignStep.filter(campaign=campaign).delete()

    await CampaignEdge.filter(campaign=campaign).delete()
    for idx, edge in enumerate(payload.edges, start=1):
        from_id = _resolve_edge_step_id(edge, client_steps, "from")
        to_id = _resolve_edge_step_id(edge, client_steps, "to")
        if not from_id or not to_id:
            raise HTTPException(
                status_code=400,
                detail="Edge references unknown steps. Save steps first or provide client_id mapping.",
            )
        await CampaignEdge.create(
            campaign=campaign,
            from_step_id=from_id,
            to_step_id=to_id,
            condition_type=edge.condition_type,
            condition_value=edge.condition_value,
            label=edge.label,
            order=edge.order or idx,
        )

    updated = (
        await Campaign.filter(id=campaign.id)
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .first()
    )
    if updated is None:
        raise HTTPException(status_code=500, detail="Campaign not found after update")
    steps = getattr(updated, "steps", []) or []
    return _serialize_campaign(updated, include_steps=True, step_count=len(steps))  # type: ignore[return-value]


@router.post("/{campaign_id}/launch", response_model=CampaignDetail)
async def launch_campaign(
    campaign_id: int, payload: LaunchRequest, user: User = Depends(authenticate)
):
    campaign = (
        await Campaign.filter(id=campaign_id)
        .prefetch_related("steps", "edges", "llm_profile", "llm_overlay_profile")
        .first()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if payload.audience_size is not None:
        campaign.audience_size = payload.audience_size  # type: ignore[assignment]

    campaign.status = "launched"  # type: ignore[assignment]
    campaign.launched_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    campaign.launch_notes = payload.notes or campaign.launch_notes  # type: ignore[assignment]
    campaign.launched_by = user  # type: ignore[assignment]
    campaign.updated_by = user  # type: ignore[assignment]
    await campaign.save()

    steps = getattr(campaign, "steps", []) or []
    return _serialize_campaign(campaign, include_steps=True, step_count=len(steps))  # type: ignore[return-value]
