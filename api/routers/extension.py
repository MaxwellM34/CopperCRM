import base64
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from tortoise.query_utils import Q

from auth.extension import get_current_user_from_google_token
from models import Lead, Thread, ThreadMessage, User
from services.thread_encryption import decrypt_text, encrypt_text, hmac_sha256

router = APIRouter(tags=["extension"])


class LinkedInEnrichRequest(BaseModel):
    linkedin_url: str
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    company_name: str | None = None
    email: str | None = None
    work_email: str | None = None
    avatar_base64: str | None = None
    avatar_content_type: str | None = None


class LinkedInEnrichResponse(BaseModel):
    lead_id: int
    action: Literal["created", "updated"]


class ThreadMessageIn(BaseModel):
    direction: Literal["outbound", "inbound"]
    message_at: datetime | None = None
    content: str
    external_message_id: str | None = None


class ThreadUpsertRequest(BaseModel):
    lead_id: int | None = None
    linkedin_url: str | None = None
    source: Literal["linkedin", "email"]
    external_thread_id: str | None = None
    messages: list[ThreadMessageIn] = Field(default_factory=list)


class ThreadMessageOut(BaseModel):
    id: int
    direction: str
    message_at: datetime | None = None
    content: str
    external_message_id: str | None = None


class ThreadOut(BaseModel):
    id: int
    lead_id: int
    source: str
    external_thread_id: str | None = None
    thread_fingerprint: str | None = None
    collected_at: datetime | None = None
    collected_by_user_id: int | None = None
    messages: list[ThreadMessageOut]


def _normalize_linkedin_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/")
    path = path or "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _decode_avatar(payload: str | None) -> bytes | None:
    if not payload:
        return None
    if payload.startswith("data:"):
        header, encoded = payload.split(",", 1)
        return base64.b64decode(encoded)
    return base64.b64decode(payload)


@router.post("/enrich/linkedin", response_model=LinkedInEnrichResponse)
async def enrich_linkedin(
    payload: LinkedInEnrichRequest,
    user: User = Depends(get_current_user_from_google_token),
):
    linkedin_url = _normalize_linkedin_url(payload.linkedin_url)
    work_email = _normalize_email(payload.work_email)
    email = _normalize_email(payload.email)

    lead = await Lead.get_or_none(linkedin_url=linkedin_url)
    if not lead and work_email:
        lead = await Lead.get_or_none(work_email__iexact=work_email)
    if not lead and email:
        lead = await Lead.get_or_none(email__iexact=email)

    now = datetime.now(timezone.utc)
    action = "updated"
    if not lead:
        lead = await Lead.create(
            linkedin_url=linkedin_url,
            first_name=_non_empty(payload.first_name) or "",
            last_name=_non_empty(payload.last_name) or "",
            email=email,
            work_email=work_email,
            job_title=_non_empty(payload.headline),
            linkedin_headline=_non_empty(payload.headline),
            linkedin_company_name=_non_empty(payload.company_name),
            last_collected_by=user,
            last_collected_at=now,
            linkedin_updated_at=now,
            updated_by=user,
            created_by=user,
        )
        action = "created"
    else:
        if _non_empty(payload.first_name):
            lead.first_name = _non_empty(payload.first_name)
        if _non_empty(payload.last_name):
            lead.last_name = _non_empty(payload.last_name)
        if _non_empty(payload.headline):
            lead.job_title = _non_empty(payload.headline)
            lead.linkedin_headline = _non_empty(payload.headline)
        if _non_empty(payload.company_name):
            lead.linkedin_company_name = _non_empty(payload.company_name)
        if email:
            lead.email = email
        if work_email:
            lead.work_email = work_email
        lead.linkedin_url = linkedin_url
        lead.last_collected_by = user
        lead.last_collected_at = now
        lead.linkedin_updated_at = now
        lead.updated_by = user

    avatar_bytes = _decode_avatar(payload.avatar_base64)
    if avatar_bytes:
        lead.avatar_bytes = avatar_bytes
        lead.avatar_content_type = _non_empty(payload.avatar_content_type)

    await lead.save()

    return LinkedInEnrichResponse(lead_id=lead.id, action=action)


@router.get("/leads/{lead_id}/avatar")
async def get_lead_avatar(
    lead_id: int,
    user: User = Depends(get_current_user_from_google_token),
):
    lead = await Lead.get_or_none(id=lead_id)
    if not lead or not lead.avatar_bytes:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return Response(
        content=lead.avatar_bytes,
        media_type=lead.avatar_content_type or "application/octet-stream",
    )


@router.post("/threads/upsert")
async def upsert_thread(
    payload: ThreadUpsertRequest,
    user: User = Depends(get_current_user_from_google_token),
):
    if not payload.lead_id and not payload.linkedin_url:
        raise HTTPException(status_code=400, detail="lead_id or linkedin_url is required")

    lead = None
    if payload.lead_id:
        lead = await Lead.get_or_none(id=payload.lead_id)
    if not lead and payload.linkedin_url:
        normalized = _normalize_linkedin_url(payload.linkedin_url)
        lead = await Lead.get_or_none(linkedin_url=normalized)
        if not lead:
            lead = await Lead.get_or_none(personal_linkedin=normalized)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    fingerprint = None
    if payload.external_thread_id:
        fingerprint = hmac_sha256(payload.external_thread_id, namespace=payload.source)
    elif payload.messages:
        combined = "\n".join(m.content.strip() for m in payload.messages if m.content.strip())
        if combined:
            fingerprint = hmac_sha256(combined, namespace=payload.source)

    thread_query = Thread.filter(lead=lead, source=payload.source)
    if payload.external_thread_id:
        thread_query = thread_query.filter(external_thread_id=payload.external_thread_id)
    elif fingerprint:
        thread_query = thread_query.filter(thread_fingerprint=fingerprint)

    thread = await thread_query.first()
    now = datetime.now(timezone.utc)
    created = False
    if not thread:
        thread = await Thread.create(
            lead=lead,
            source=payload.source,
            external_thread_id=payload.external_thread_id,
            thread_fingerprint=fingerprint,
            collected_by=user,
            collected_at=now,
        )
        created = True
    else:
        thread.collected_by = user
        thread.collected_at = now
        if payload.external_thread_id and not thread.external_thread_id:
            thread.external_thread_id = payload.external_thread_id
        if fingerprint and not thread.thread_fingerprint:
            thread.thread_fingerprint = fingerprint
        await thread.save()

    created_messages = 0
    for message in payload.messages:
        content = message.content.strip()
        if not content:
            continue

        content_hash = hmac_sha256(f"{message.direction}:{content}", namespace=payload.source)
        filters = Q(content_hash=content_hash)
        if message.external_message_id:
            filters |= Q(external_message_id=message.external_message_id)

        exists = await ThreadMessage.filter(thread=thread).filter(filters).exists()
        if exists:
            continue

        await ThreadMessage.create(
            thread=thread,
            source=payload.source,
            direction=message.direction,
            message_at=message.message_at,
            encrypted_content=encrypt_text(content),
            content_hash=content_hash,
            external_message_id=message.external_message_id,
        )
        created_messages += 1

    return {
        "thread_id": thread.id,
        "created_messages": created_messages,
        "updated": not created,
    }


@router.get("/threads/{thread_id}", response_model=ThreadOut)
async def get_thread(
    thread_id: int,
    user: User = Depends(get_current_user_from_google_token),
):
    thread = await Thread.get_or_none(id=thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = (
        await ThreadMessage.filter(thread=thread)
        .order_by("message_at", "id")
    )

    decrypted = [
        ThreadMessageOut(
            id=message.id,
            direction=message.direction,
            message_at=message.message_at,
            content=decrypt_text(message.encrypted_content),
            external_message_id=message.external_message_id,
        )
        for message in messages
    ]

    return ThreadOut(
        id=thread.id,
        lead_id=thread.lead_id,
        source=thread.source,
        external_thread_id=thread.external_thread_id,
        thread_fingerprint=thread.thread_fingerprint,
        collected_at=thread.collected_at,
        collected_by_user_id=thread.collected_by_id,
        messages=decrypted,
    )
