from datetime import datetime
from typing import Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.authenticate import authenticate
from models import Lead, User

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadDisplay(BaseModel):
    id: int
    email: Optional[str]
    work_email: Optional[str]
    gender: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    company_id: Optional[int]
    company_name: Optional[str]
    job_title: Optional[str]
    person_address: Optional[str]
    country: Optional[str]
    personal_linkedin: Optional[str]
    seniority: Optional[str]
    departments: Optional[str]


class LeadDetail(BaseModel):
    id: int
    email: Optional[str]
    work_email: Optional[str]
    gender: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    company_id: Optional[int]
    company_name: Optional[str]
    job_title: Optional[str]
    person_address: Optional[str]
    country: Optional[str]
    personal_linkedin: Optional[str]
    seniority: Optional[str]
    departments: Optional[str]
    industries: Optional[str]
    profile_summary: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


@router.get("/display", response_model=list[LeadDisplay])
async def displayLeads(user: User = Depends(authenticate)):
    rows = await Lead.all().prefetch_related("company").values(
        "id",
        "email",
        "work_email",
        "gender",
        "first_name",
        "last_name",
        "avatar_url",
        "company_id",
        "company__company_name",
        "job_title",
        "person_address",
        "country",
        "personal_linkedin",
        "seniority",
        "departments",
    )
    for row in rows:
        row["company_name"] = row.pop("company__company_name", None)
    return rows


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead(lead_id: int, user: User = Depends(authenticate)):
    lead = await Lead.filter(id=lead_id).prefetch_related("company").first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    company = getattr(lead, "company", None)
    company_id = cast(int, company.id) if company else None
    company_name = cast(str, company.company_name) if company else None
    return LeadDetail(
        id=cast(int, lead.id),
        email=cast(Optional[str], lead.email),
        work_email=cast(Optional[str], lead.work_email),
        gender=cast(Optional[str], lead.gender),
        first_name=cast(Optional[str], lead.first_name),
        last_name=cast(Optional[str], lead.last_name),
        avatar_url=cast(Optional[str], getattr(lead, "avatar_url", None)),
        company_id=company_id,
        company_name=company_name,
        job_title=cast(Optional[str], lead.job_title),
        person_address=cast(Optional[str], lead.person_address),
        country=cast(Optional[str], lead.country),
        personal_linkedin=cast(Optional[str], lead.personal_linkedin),
        seniority=cast(Optional[str], lead.seniority),
        departments=cast(Optional[str], lead.departments),
        industries=cast(Optional[str], lead.industries),
        profile_summary=cast(Optional[str], lead.profile_summary),
        created_at=cast(Optional[datetime], getattr(lead, "created_at", None)),
        updated_at=cast(Optional[datetime], getattr(lead, "updated_at", None)),
    )
