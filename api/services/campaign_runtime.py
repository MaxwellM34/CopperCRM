from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

from fastapi import HTTPException
from tortoise.expressions import Q

from models import (
    Campaign,
    CampaignEdge,
    CampaignEmailDraft,
    CampaignStep,
    Lead,
    LeadActivity,
    LeadCampaignState,
    LLMProfile,
    OutboundInbox,
    OutboundMessage,
    User,
)
from services.email_generation import build_lead_context, get_openai_client
from services.email_sender import (
    build_raw_email,
    build_reply_subject,
    normalize_subject,
    send_raw_email,
)
from services.imap_client import fetch_new_messages, fetch_thread_messages, render_thread_text
from services.tracking import build_tracking_id, build_tracking_url, build_unsubscribe_token, build_unsubscribe_url

DEFAULT_STEP_MODEL = "gpt-4o-mini"

POINTS_BY_ACTIVITY = {
    "email_sent": 0,
    "email_open": 1,
    "email_reply": 5,
    "campaign_enrolled": 0,
    "goal_reached": 10,
}

UNSUBSCRIBE_REGEX = re.compile(r"\b(unsubscribe|stop|opt\s?out|remove me)\b", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lead_email(lead: Lead) -> str | None:
    return lead.work_email or lead.email


def _safe_step_config(step: CampaignStep) -> dict:
    return step.config or {}


def _apply_entry_filters(query, filters: Iterable[dict]):
    allowed = {
        "country": "country",
        "industries": "industries",
        "departments": "departments",
        "seniority": "seniority",
        "job_title": "job_title",
        "company": "company__company_name",
    }
    for entry in filters or []:
        field = (entry.get("field") or "").strip()
        op = (entry.get("op") or "equals").strip().lower()
        value = entry.get("value")
        if not field or value in {None, ""}:
            continue
        column = allowed.get(field)
        if not column:
            continue
        if op == "equals":
            query = query.filter(**{column: value})
        elif op == "contains":
            query = query.filter(**{f"{column}__icontains": value})
        elif op == "in":
            values = value if isinstance(value, list) else [v.strip() for v in str(value).split(",") if v.strip()]
            if values:
                query = query.filter(**{f"{column}__in": values})
    return query


def _profile_version(profile: LLMProfile | None) -> str | None:
    if not profile:
        return None
    ts = getattr(profile, "updated_at", None)
    if ts and hasattr(ts, "isoformat"):
        return ts.isoformat()
    return "v1"


def _reply_wait_hours(step: CampaignStep) -> int:
    config = _safe_step_config(step)
    return int(config.get("reply_wait_hours") or 48)


def _delay_hours(step: CampaignStep) -> int:
    config = _safe_step_config(step)
    return int(config.get("duration_hours") or 24)


def _activity_points(activity_type: str) -> int:
    return POINTS_BY_ACTIVITY.get(activity_type, 0)


async def _record_activity(
    *,
    lead: Lead,
    campaign: Campaign | None,
    inbox: OutboundInbox | None,
    activity_type: str,
    metadata: dict | None = None,
) -> None:
    points = _activity_points(activity_type)
    await LeadActivity.create(
        lead=lead,
        campaign=campaign,
        inbox=inbox,
        activity_type=activity_type,
        metadata=metadata or {},
    )
    lead.last_activity_at = _now()  # type: ignore[assignment]
    lead.last_activity_type = activity_type  # type: ignore[assignment]
    if points:
        lead.points = (lead.points or 0) + points  # type: ignore[assignment]
    await lead.save()


async def _award_points(
    *,
    lead: Lead,
    campaign: Campaign | None,
    inbox: OutboundInbox | None,
    points: int,
    reason: str | None = None,
    step_id: int | None = None,
) -> None:
    if points == 0:
        return
    lead.points = (lead.points or 0) + points  # type: ignore[assignment]
    lead.last_activity_at = _now()  # type: ignore[assignment]
    lead.last_activity_type = "points_awarded"  # type: ignore[assignment]
    await lead.save()
    await LeadActivity.create(
        lead=lead,
        campaign=campaign,
        inbox=inbox,
        activity_type="points_awarded",
        metadata={"points": points, "reason": reason, "step_id": step_id},
    )


async def _reset_inbox_daily_sent(inbox: OutboundInbox) -> None:
    if inbox.last_reset_at and inbox.last_reset_at.date() == _now().date():
        return
    inbox.daily_sent = 0  # type: ignore[assignment]
    inbox.last_reset_at = _now()  # type: ignore[assignment]
    await inbox.save()


async def select_inbox_for_lead(lead: Lead) -> OutboundInbox:
    inboxes = await OutboundInbox.filter(active=True).order_by("daily_sent", "id")
    if not inboxes:
        raise HTTPException(status_code=400, detail="No active outbound inboxes configured")

    available: list[OutboundInbox] = []
    for inbox in inboxes:
        await _reset_inbox_daily_sent(inbox)
        if inbox.daily_sent < inbox.daily_cap:
            available.append(inbox)

    if not available:
        raise HTTPException(status_code=429, detail="All outbound inboxes are at their daily cap")

    return min(available, key=lambda i: i.daily_sent / max(i.daily_cap, 1))


async def _entry_step(campaign: Campaign) -> CampaignStep | None:
    step = await CampaignStep.filter(campaign=campaign, step_type="entry").order_by("sequence").first()
    if step:
        return step
    return await CampaignStep.filter(campaign=campaign).order_by("sequence").first()


async def enroll_leads_for_campaign(campaign: Campaign) -> int:
    max_total = campaign.audience_size
    existing_count = await LeadCampaignState.filter(campaign=campaign).count()
    if max_total is not None and existing_count >= max_total:
        return 0
    limit = None
    if max_total is not None:
        limit = max_total - existing_count
        if limit <= 0:
            return 0

    entry = await _entry_step(campaign)
    if entry is None:
        return 0

    contacted_ids = await OutboundMessage.filter(direction="outbound").values_list("lead_id", flat=True)
    active_statuses = [
        "pending",
        "active",
        "waiting_reply",
        "waiting_delay",
        "waiting_condition",
        "waiting_approval",
    ]
    leads = (
        Lead.filter(opted_out=False)
        .exclude(campaign_states__campaign=campaign)
        .exclude(campaign_states__status__in=active_statuses)
        .exclude(id__in=list(contacted_ids))
        .filter(Q(work_email__not_isnull=True) | Q(email__not_isnull=True))
        .order_by("id")
    )

    entry_config = _safe_step_config(entry) if entry else {}
    leads = _apply_entry_filters(leads, entry_config.get("filters") or [])
    if limit:
        leads = leads.limit(limit)

    enrolled = 0
    for lead in await leads:
        inbox = await select_inbox_for_lead(lead)
        await LeadCampaignState.create(
            lead=lead,
            campaign=campaign,
            status="active",
            current_step=entry,
            assigned_inbox=inbox,
            next_step_at=_now(),
        )
        await _record_activity(
            lead=lead,
            campaign=campaign,
            inbox=inbox,
            activity_type="campaign_enrolled",
            metadata={"campaign_id": campaign.id},
        )
        enrolled += 1

    return enrolled


async def _find_edge(
    campaign: Campaign,
    step: CampaignStep,
    condition_type: str,
    condition_value: str | None = None,
) -> CampaignEdge | None:
    qs = CampaignEdge.filter(campaign=campaign, from_step=step).order_by("order", "id")
    if condition_type:
        qs = qs.filter(condition_type=condition_type)
    if condition_value:
        if condition_type == "intent":
            qs = qs.filter(condition_value__iexact=condition_value)
        else:
            qs = qs.filter(condition_value=condition_value)
    edge = await qs.first()
    if edge:
        return edge
    if condition_type != "always":
        return await CampaignEdge.filter(
            campaign=campaign, from_step=step, condition_type="always"
        ).order_by("order", "id").first()
    return None


async def _intent_labels_for_step(campaign: Campaign, step: CampaignStep) -> list[str]:
    edges = (
        await CampaignEdge.filter(
            campaign=campaign,
            from_step=step,
            condition_type="intent",
        )
        .order_by("order", "id")
    )
    labels: list[str] = []
    for edge in edges:
        value = (edge.condition_value or "").strip().lower()
        if value and value not in labels:
            labels.append(value)
    return labels


async def _transition_to_edge(
    state: LeadCampaignState,
    edge: CampaignEdge | None,
    fallback_to_sequence: bool = True,
) -> None:
    if edge:
        state.current_step_id = edge.to_step_id  # type: ignore[assignment]
        state.status = "active"  # type: ignore[assignment]
        state.next_step_at = _now()  # type: ignore[assignment]
        await state.save()
        return
    if fallback_to_sequence:
        next_step = (
            await CampaignStep.filter(campaign=state.campaign, sequence__gt=state.current_step.sequence)  # type: ignore[arg-type]
            .order_by("sequence")
            .first()
        )
        if next_step:
            state.current_step = next_step  # type: ignore[assignment]
            state.status = "active"  # type: ignore[assignment]
            state.next_step_at = _now()  # type: ignore[assignment]
            await state.save()
            return
    state.status = "completed"  # type: ignore[assignment]
    state.next_step_at = None  # type: ignore[assignment]
    await state.save()


def _build_step_instructions(step: CampaignStep) -> str:
    config = _safe_step_config(step)
    parts: list[str] = []
    if step.prompt_template:
        parts.append(step.prompt_template.strip())
    if config.get("tone"):
        parts.append(f"Tone: {config['tone']}.")
    if config.get("cta"):
        parts.append(f"CTA: {config['cta']}.")
    if config.get("variant"):
        parts.append(f"Variant: {config['variant']}.")
    if config.get("personalization"):
        parts.append(f"Personalization: {config['personalization']}.")
    if config.get("reply_mode"):
        parts.append("This is a reply inside an existing thread. Answer the latest question first.")
    return " ".join(parts)


async def _generate_email_body(
    *,
    lead: Lead,
    campaign: Campaign,
    step: CampaignStep,
    base_profile: LLMProfile | None,
    overlay_profile: LLMProfile | None,
    thread_text: str | None,
) -> str:
    client = get_openai_client()
    lead_context = build_lead_context(lead)
    config = _safe_step_config(step)
    model = config.get("ai_model") or config.get("model") or DEFAULT_STEP_MODEL
    step_notes = _build_step_instructions(step)

    system = (
        "You are the Copper CRM outreach AI. Follow the base and overlay rules. "
        "Never fabricate data. Use provided lead/company and thread context. "
        "If browsing is available, reference recent, verifiable company or person news only."
    )
    if base_profile:
        system += f"\nBase rules: {base_profile.rules}"
    if overlay_profile:
        system += f"\nOverlay rules: {overlay_profile.rules}"
    if campaign.ai_brief:
        system += f"\nCampaign brief: {campaign.ai_brief}"

    user = "Write the email body only. No subject line.\n"
    if step_notes:
        user += f"Step instructions: {step_notes}\n"
    user += f"Lead context:\n{lead_context}\n"
    if thread_text:
        user += f"\nThread so far:\n{thread_text}\n"

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.6,
        max_tokens=420,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("Empty response from model")
    return content


async def _classify_reply_intent(
    thread_text: str,
    allowed_labels: list[str] | None = None,
    model: str | None = None,
) -> str:
    if UNSUBSCRIBE_REGEX.search(thread_text):
        return "unsubscribe"
    client = get_openai_client()
    if allowed_labels:
        label_list = ", ".join(allowed_labels)
        system = f"Classify the reply intent into one label: {label_list}. If none fit, return other."
    else:
        system = "Classify the reply intent into one label: meeting_request, question, negative, no_interest, other."
    user = f"Thread:\n{thread_text}\n\nReturn only the label."
    response = await client.chat.completions.create(
        model=model or DEFAULT_STEP_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=10,
    )
    label = (response.choices[0].message.content or "").strip().lower()
    if allowed_labels:
        return label if label in allowed_labels else "other"
    if label in {"meeting_request", "question", "negative", "no_interest"}:
        return label
    return "other"


def _build_html_body(text_body: str, tracking_url: str, unsubscribe_url: str) -> str:
    escaped = text_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped = escaped.replace("\n", "<br />\n")
    return (
        f"{escaped}<br /><br />"
        f'<a href="{unsubscribe_url}">Remove from email list</a>'
        f'<img src="{tracking_url}" alt="" width="1" height="1" style="display:none;" />'
    )


def _render_html_preview(text_body: str) -> str:
    escaped = text_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return escaped.replace("\n", "<br />\n")


def _build_text_body(text_body: str, unsubscribe_url: str) -> str:
    return f"{text_body}\n\nRemove from email list: {unsubscribe_url}"


async def _fetch_thread_text(inbox: OutboundInbox, lead_email: str) -> str | None:
    if not (inbox.imap_host and inbox.imap_username and inbox.imap_password):
        return None
    inbox_folder = inbox.imap_folder or "INBOX"
    sent_folder = inbox.imap_sent_folder or "Sent"
    messages = await asyncio.to_thread(
        fetch_thread_messages,
        host=inbox.imap_host,
        port=inbox.imap_port,
        use_ssl=bool(inbox.imap_use_ssl),
        username=inbox.imap_username,
        password=inbox.imap_password,
        inbox_folder=inbox_folder,
        sent_folder=sent_folder,
        lead_email=lead_email,
    )
    if not messages:
        return None
    return render_thread_text(messages)


async def create_email_draft(
    *,
    state: LeadCampaignState,
    campaign: Campaign,
    step: CampaignStep,
) -> CampaignEmailDraft:
    lead = state.lead
    lead_email = _lead_email(lead)
    if not lead_email:
        raise HTTPException(status_code=400, detail="Lead has no email")

    inbox = state.assigned_inbox or await select_inbox_for_lead(lead)
    if state.assigned_inbox is None:
        state.assigned_inbox = inbox  # type: ignore[assignment]
        await state.save()

    base_profile = campaign.llm_profile
    overlay_profile = campaign.llm_overlay_profile
    thread_text = await _fetch_thread_text(inbox, lead_email)
    body = await _generate_email_body(
        lead=lead,
        campaign=campaign,
        step=step,
        base_profile=base_profile,
        overlay_profile=overlay_profile,
        thread_text=thread_text,
    )
    base_version = _profile_version(base_profile)
    overlay_version = _profile_version(overlay_profile)

    last_message = (
        await OutboundMessage.filter(lead=lead, campaign=campaign, direction="outbound")
        .order_by("-sent_at", "-id")
        .first()
    )
    if thread_text and last_message and last_message.subject:
        subject = build_reply_subject(last_message.subject)
    else:
        subject = normalize_subject(step.config.get("subject") if step.config else None)

    draft = await CampaignEmailDraft.create(
        campaign=campaign,
        lead=lead,
        inbox=inbox,
        step=step,
        subject=subject,
        body_text=body,
        body_html=_render_html_preview(body),
        status="pending",
        from_email=inbox.email_address,
        to_email=lead_email,
        llm_profile_version=base_version,
        llm_profile_name=base_profile.name if base_profile else None,
        llm_profile_rules=base_profile.rules if base_profile else None,
        llm_overlay_profile_version=overlay_version,
        llm_overlay_profile_name=overlay_profile.name if overlay_profile else None,
        llm_overlay_profile_rules=overlay_profile.rules if overlay_profile else None,
    )

    state.status = "waiting_approval"  # type: ignore[assignment]
    await state.save()

    await _record_activity(
        lead=lead,
        campaign=campaign,
        inbox=inbox,
        activity_type="draft_created",
        metadata={"draft_id": draft.id, "step_id": step.id},
    )
    return draft


async def send_draft_email(
    *,
    draft: CampaignEmailDraft,
    user: User | None,
) -> OutboundMessage:
    lead = draft.lead
    campaign = draft.campaign
    inbox = draft.inbox
    if inbox is None:
        raise HTTPException(status_code=400, detail="Draft has no inbox assigned")
    to_email = draft.to_email or _lead_email(lead)
    if not to_email:
        raise HTTPException(status_code=400, detail="Lead has no email")

    tracking_id = build_tracking_id()
    token = build_unsubscribe_token(lead.id, to_email)
    unsubscribe_url = build_unsubscribe_url(token)
    tracking_url = build_tracking_url(tracking_id)
    base_profile = campaign.llm_profile
    overlay_profile = campaign.llm_overlay_profile
    base_version = draft.llm_profile_version or _profile_version(base_profile)
    overlay_version = draft.llm_overlay_profile_version or _profile_version(overlay_profile)

    body_text = _build_text_body(draft.body_text, unsubscribe_url)
    body_html = _build_html_body(draft.body_text, tracking_url, unsubscribe_url)

    last_message = (
        await OutboundMessage.filter(lead=lead, campaign=campaign, direction="outbound")
        .order_by("-sent_at", "-id")
        .first()
    )
    in_reply_to = last_message.message_id if last_message else None
    references = last_message.references or (last_message.message_id if last_message else None)

    raw_bytes, message_id = build_raw_email(
        from_email=inbox.email_address,
        from_name=inbox.display_name,
        to_email=to_email,
        subject=normalize_subject(draft.subject),
        text_body=body_text,
        html_body=body_html,
        reply_to=inbox.reply_to,
        in_reply_to=in_reply_to,
        references=references,
        list_unsubscribe=unsubscribe_url,
    )

    await asyncio.to_thread(
        send_raw_email,
        raw_bytes=raw_bytes,
        source=inbox.email_address,
        to_email=to_email,
        configuration_set=inbox.ses_configuration_set,
    )

    inbox.daily_sent = (inbox.daily_sent or 0) + 1  # type: ignore[assignment]
    await inbox.save()

    thread_id = last_message.thread_id if last_message and last_message.thread_id else message_id
    message = await OutboundMessage.create(
        lead=lead,
        campaign=campaign,
        inbox=inbox,
        step=draft.step,
        direction="outbound",
        message_id=message_id,
        thread_id=thread_id,
        subject=normalize_subject(draft.subject),
        in_reply_to=in_reply_to,
        references=references,
        sent_at=_now(),
        status="sent",
        recipient_email=to_email,
        tracking_id=tracking_id,
        llm_profile_version=base_version,
        llm_profile_name=draft.llm_profile_name or (base_profile.name if base_profile else None),
        llm_profile_rules=draft.llm_profile_rules or (base_profile.rules if base_profile else None),
        llm_overlay_profile_version=overlay_version,
        llm_overlay_profile_name=draft.llm_overlay_profile_name or (overlay_profile.name if overlay_profile else None),
        llm_overlay_profile_rules=draft.llm_overlay_profile_rules or (overlay_profile.rules if overlay_profile else None),
    )

    draft.status = "sent"  # type: ignore[assignment]
    draft.sent_at = _now()  # type: ignore[assignment]
    draft.approved_at = _now()  # type: ignore[assignment]
    draft.approved_by = user  # type: ignore[assignment]
    await draft.save()

    state = await LeadCampaignState.filter(lead=lead, campaign=campaign).first()
    if state and draft.step:
        state.status = "waiting_reply"  # type: ignore[assignment]
        state.current_step = draft.step  # type: ignore[assignment]
        state.last_sent_at = _now()  # type: ignore[assignment]
        state.last_message_id = message_id  # type: ignore[assignment]
        state.thread_id = thread_id  # type: ignore[assignment]
        state.next_step_at = _now() + timedelta(hours=_reply_wait_hours(draft.step))  # type: ignore[assignment]
        await state.save()

    await _record_activity(
        lead=lead,
        campaign=campaign,
        inbox=inbox,
        activity_type="email_sent",
        metadata={"message_id": message_id, "draft_id": draft.id},
    )

    return message


async def process_reply_events(inbox: OutboundInbox) -> int:
    if not (inbox.imap_host and inbox.imap_username and inbox.imap_password):
        return 0

    messages, newest_uid = await asyncio.to_thread(
        fetch_new_messages,
        host=inbox.imap_host,
        port=inbox.imap_port,
        use_ssl=bool(inbox.imap_use_ssl),
        username=inbox.imap_username,
        password=inbox.imap_password,
        folder=inbox.imap_folder or "INBOX",
        last_uid=inbox.imap_last_uid,
    )

    reply_count = 0
    for msg in messages:
        from_email = msg.get("from")
        if not from_email or from_email.lower() == inbox.email_address.lower():
            continue
        lead = await Lead.filter(Q(work_email=from_email) | Q(email=from_email)).first()
        if not lead:
            continue
        campaign_state = await LeadCampaignState.filter(
            lead=lead,
            status__in=["waiting_reply", "waiting_delay", "waiting_condition", "waiting_approval", "active"],
        ).prefetch_related("current_step", "campaign").order_by("-updated_at").first()
        campaign = campaign_state.campaign if campaign_state else None

        await OutboundMessage.get_or_create(
            message_id=msg.get("message_id") or f"inbound-{msg.get('uid')}",
            defaults={
                "lead": lead,
                "campaign": campaign,
                "inbox": inbox,
                "direction": "inbound",
                "thread_id": msg.get("in_reply_to") or msg.get("references"),
                "subject": msg.get("subject"),
                "in_reply_to": msg.get("in_reply_to"),
                "references": msg.get("references"),
                "sent_at": msg.get("date"),
                "status": "received",
                "recipient_email": inbox.email_address,
            },
        )

        await _record_activity(
            lead=lead,
            campaign=campaign,
            inbox=inbox,
            activity_type="email_reply",
            metadata={"subject": msg.get("subject"), "message_id": msg.get("message_id")},
        )

        if UNSUBSCRIBE_REGEX.search(msg.get("body", "")):
            lead.opted_out = True  # type: ignore[assignment]
            lead.opted_out_at = _now()  # type: ignore[assignment]
            await lead.save()

        reply_step = campaign_state.current_step if campaign_state else None
        if campaign:
            last_outbound = (
                await OutboundMessage.filter(
                    lead=lead,
                    campaign=campaign,
                    direction="outbound",
                )
                .prefetch_related("step")
                .order_by("-sent_at", "-id")
                .first()
            )
            if last_outbound and getattr(last_outbound, "step", None):
                reply_step = last_outbound.step
        if campaign_state and reply_step:
            edge = await _find_edge(campaign_state.campaign, reply_step, "reply")
            if edge:
                await _transition_to_edge(campaign_state, edge, fallback_to_sequence=False)
        reply_count += 1

    if newest_uid is not None and newest_uid != inbox.imap_last_uid:
        inbox.imap_last_uid = newest_uid  # type: ignore[assignment]
        inbox.imap_last_checked_at = _now()  # type: ignore[assignment]
        await inbox.save()

    return reply_count


async def process_state(state: LeadCampaignState) -> None:
    lead = state.lead
    campaign = state.campaign
    step = state.current_step

    if lead.opted_out:
        state.status = "stopped"  # type: ignore[assignment]
        await state.save()
        return

    now = _now()

    if state.status == "waiting_approval":
        return

    if state.status == "waiting_delay":
        if state.next_step_at and state.next_step_at > now:
            return
        edge = await _find_edge(campaign, step, "always") if step else None
        await _transition_to_edge(state, edge)
        return

    if state.status == "waiting_condition":
        if state.next_step_at and state.next_step_at > now:
            return
        if step:
            config = _safe_step_config(step)
            event = (config.get("event") or "email_open").strip().lower()
            if event in {"reply", "email_reply"}:
                no_type = "no_reply"
            elif event in {"open", "opened", "email_open"}:
                no_type = "no_open"
            else:
                no_type = "no_event"
            edge = await _find_edge(campaign, step, no_type)
            await _transition_to_edge(state, edge)
        else:
            state.status = "completed"  # type: ignore[assignment]
            await state.save()
        return

    if state.status == "waiting_reply":
        if state.next_step_at and state.next_step_at > now:
            return
        if step:
            edge = await _find_edge(campaign, step, "no_reply")
            await _transition_to_edge(state, edge)
        else:
            state.status = "completed"  # type: ignore[assignment]
            await state.save()
        return

    if step is None:
        entry = await _entry_step(campaign)
        if entry is None:
            state.status = "completed"  # type: ignore[assignment]
            await state.save()
            return
        state.current_step = entry  # type: ignore[assignment]
        state.status = "active"  # type: ignore[assignment]
        state.next_step_at = now  # type: ignore[assignment]
        await state.save()
        step = entry

    if step.step_type == "entry":
        edge = await _find_edge(campaign, step, "always")
        await _transition_to_edge(state, edge)
        return

    if step.step_type == "delay":
        if state.status != "waiting_delay":
            state.status = "waiting_delay"  # type: ignore[assignment]
            state.next_step_at = now + timedelta(hours=_delay_hours(step))  # type: ignore[assignment]
            await state.save()
        return

    if step.step_type == "condition":
        config = _safe_step_config(step)
        event = (config.get("event") or "email_open").strip().lower()
        window_hours = int(config.get("window_hours") or 48)
        since = state.last_sent_at or state.updated_at or state.created_at or now
        activity_type = event
        if event in {"open", "opened", "email_open"}:
            activity_type = "email_open"
            yes_type = "open"
            no_type = "no_open"
        elif event in {"reply", "email_reply"}:
            activity_type = "email_reply"
            yes_type = "reply"
            no_type = "no_reply"
        else:
            yes_type = "event"
            no_type = "no_event"

        activity = await LeadActivity.filter(
            lead=lead,
            activity_type=activity_type,
            occurred_at__gte=since,
        ).order_by("-occurred_at").first()

        if activity:
            edge = await _find_edge(campaign, step, yes_type)
            await _transition_to_edge(state, edge)
            return

        expires_at = since + timedelta(hours=window_hours)
        if now < expires_at:
            state.status = "waiting_condition"  # type: ignore[assignment]
            state.next_step_at = expires_at  # type: ignore[assignment]
            await state.save()
            return

        edge = await _find_edge(campaign, step, no_type)
        await _transition_to_edge(state, edge)
        return

    if step.step_type == "ai_email":
        existing = await CampaignEmailDraft.filter(
            campaign=campaign, lead=lead, step=step, status="pending"
        ).first()
        if existing:
            state.status = "waiting_approval"  # type: ignore[assignment]
            await state.save()
            return
        await create_email_draft(state=state, campaign=campaign, step=step)
        return

    if step.step_type == "ai_decision":
        config = _safe_step_config(step)
        decision_model = config.get("model") or config.get("ai_model")
        inbox = state.assigned_inbox
        lead_email = _lead_email(lead)
        thread_text = None
        if inbox and lead_email:
            thread_text = await _fetch_thread_text(inbox, lead_email)
        if not thread_text:
            edge = await _find_edge(campaign, step, "no_reply")
            await _transition_to_edge(state, edge)
            return
        allowed_labels = await _intent_labels_for_step(campaign, step)
        intent = await _classify_reply_intent(thread_text, allowed_labels or None, decision_model)
        edge = await _find_edge(campaign, step, "intent", intent)
        await _transition_to_edge(state, edge)
        await _record_activity(
            lead=lead,
            campaign=campaign,
            inbox=inbox,
            activity_type="decision",
            metadata={"intent": intent, "step_id": step.id},
        )
        return

    if step.step_type == "goal":
        state.status = "completed"  # type: ignore[assignment]
        await state.save()
        await _record_activity(
            lead=lead,
            campaign=campaign,
            inbox=state.assigned_inbox,
            activity_type="goal_reached",
            metadata={"step_id": step.id},
        )
        return

    if step.step_type == "points":
        config = _safe_step_config(step)
        points = int(config.get("points") or 0)
        reason = config.get("reason")
        await _award_points(
            lead=lead,
            campaign=campaign,
            inbox=state.assigned_inbox,
            points=points,
            reason=reason,
            step_id=step.id,
        )
        edge = await _find_edge(campaign, step, "always")
        await _transition_to_edge(state, edge)
        return

    if step.step_type == "exit":
        state.status = "stopped"  # type: ignore[assignment]
        await state.save()
        return


async def run_campaign_tick(campaign_id: int | None = None) -> dict:
    if campaign_id:
        campaigns = await Campaign.filter(id=campaign_id, status="launched").prefetch_related(
            "steps", "edges", "llm_profile", "llm_overlay_profile"
        )
    else:
        campaigns = await Campaign.filter(status="launched").prefetch_related(
            "steps", "edges", "llm_profile", "llm_overlay_profile"
        )

    inboxes = await OutboundInbox.filter(active=True)
    replies = 0
    for inbox in inboxes:
        replies += await process_reply_events(inbox)

    enrolled = 0
    processed = 0

    for campaign in campaigns:
        enrolled += await enroll_leads_for_campaign(campaign)
        states = (
            await LeadCampaignState.filter(campaign=campaign)
            .prefetch_related("lead", "current_step", "assigned_inbox", "campaign")
            .order_by("next_step_at", "id")
        )
        for state in states:
            if state.next_step_at and state.next_step_at > _now():
                continue
            await process_state(state)
            processed += 1

    return {"campaigns": len(campaigns), "enrolled": enrolled, "processed": processed, "replies": replies}
