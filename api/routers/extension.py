from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from auth.authenticate import authenticate
from models import Company, Lead, User
from services.linkedin_lookup import find_lead_by_linkedin, lead_to_profile, normalize_linkedin_url

router = APIRouter(prefix="/extension", tags=["extension"])


class ExtensionLookupRequest(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    linkedin_url: Optional[str] = Field(default=None, alias="url")
    name: Optional[str] = None


class ExtensionProfileResponse(BaseModel):
    found: bool
    name: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None


class ExtensionUpsertRequest(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    linkedin_url: Optional[str] = Field(default=None, alias="url")
    name: Optional[str] = None
    job_title: Optional[str] = Field(default=None, alias="jobTitle")
    company: Optional[str] = None
    avatar_url: Optional[str] = Field(default=None, alias="avatarUrl")
    source: Optional[str] = None
    create_if_missing: bool = Field(default=True, alias="createIfMissing")


class ExtensionUpsertResponse(BaseModel):
    found: bool
    created: bool = False
    updated: bool = False
    lead_id: Optional[int] = None
    name: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _split_name(full_name: Optional[str]) -> tuple[str, str]:
    name = _clean(full_name) or ""
    parts = [part for part in name.split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _set_if_changed(obj: object, field: str, value: Optional[str]) -> bool:
    if value is None:
        return False
    current = getattr(obj, field, None)
    current_value = (current or "").strip() if isinstance(current, str) else current
    next_value = value.strip() if isinstance(value, str) else value
    if current_value == next_value:
        return False
    setattr(obj, field, next_value)
    return True


def _normalize_source(source: Optional[str]) -> str:
    return _clean(source) or "extension"


@router.post(
    "/profile",
    response_model=ExtensionProfileResponse,
    response_model_exclude_none=True,
)
async def lookup_profile(
    payload: ExtensionLookupRequest,
    user: User = Depends(authenticate),
):
    if not payload.linkedin_url:
        raise HTTPException(status_code=400, detail="Missing linkedin_url")

    lead = await find_lead_by_linkedin(payload.linkedin_url)
    if not lead:
        return ExtensionProfileResponse(found=False)

    profile = lead_to_profile(lead)
    return ExtensionProfileResponse(found=True, **profile)


@router.post(
    "/lead",
    response_model=ExtensionUpsertResponse,
    response_model_exclude_none=True,
)
async def upsert_lead(
    payload: ExtensionUpsertRequest,
    user: User = Depends(authenticate),
):
    raw_url = _clean(payload.linkedin_url)
    if not raw_url:
        raise HTTPException(status_code=400, detail="Missing linkedin_url")

    normalized_url = normalize_linkedin_url(raw_url)
    source = _normalize_source(payload.source)
    name = _clean(payload.name)
    job_title = _clean(payload.job_title)
    company_name = _clean(payload.company)
    avatar_url = _clean(payload.avatar_url)

    company_obj = None
    if company_name:
        company_obj = await Company.filter(company_name__iexact=company_name).first()
        if company_obj is None:
            company_obj = await Company.create(
                company_name=company_name,
                created_by=user,
                updated_by=user,
            )

    lead = await find_lead_by_linkedin(normalized_url)
    if lead is None and not payload.create_if_missing:
        return ExtensionUpsertResponse(found=False, created=False, updated=False)

    created = False
    updated = False

    if lead is None:
        first_name, last_name = _split_name(name)
        if not first_name:
            first_name = "Unknown"
        lead = await Lead.create(
            first_name=first_name,
            last_name=last_name,
            job_title=job_title,
            personal_linkedin=normalized_url,
            avatar_url=avatar_url,
            company=company_obj,
            created_by=user,
            updated_by=user,
            created_source=source,
            updated_source=source,
        )
        created = True
    else:
        changed = False
        first_name, last_name = _split_name(name)
        changed |= _set_if_changed(lead, "first_name", first_name or None)
        changed |= _set_if_changed(lead, "last_name", last_name or None)
        changed |= _set_if_changed(lead, "job_title", job_title)
        changed |= _set_if_changed(lead, "personal_linkedin", normalized_url)
        changed |= _set_if_changed(lead, "avatar_url", avatar_url)
        if company_obj and getattr(lead, "company_id", None) != company_obj.id:
            lead.company = company_obj
            changed = True
        if changed:
            lead.updated_by = user
            lead.updated_source = source
            await lead.save()
            updated = True

    profile = lead_to_profile(lead)
    return ExtensionUpsertResponse(
        found=True,
        created=created,
        updated=updated,
        lead_id=lead.id,
        **profile,
    )
