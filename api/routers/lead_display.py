from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth.authenticate import authenticate
from models import Lead, LeadActivity, User

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadDisplay(BaseModel):
    id: int
    email: Optional[str]
    work_email: Optional[str]
    gender: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]
    job_title: Optional[str]
    person_address: Optional[str]
    country: Optional[str]
    personal_linkedin: Optional[str]
    seniority: Optional[str]
    departments: Optional[str]


@router.get("/display", response_model=list[LeadDisplay])
async def displayLeads(user: User = Depends(authenticate)):
    rows = await Lead.all().prefetch_related("company").values(
        "id",
        "email",
        "work_email",
        "gender",
        "first_name",
        "last_name",
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


class LeadActivityItem(BaseModel):
    activity_type: str
    occurred_at: str | None = None
    metadata: dict = {}


class LeadDetail(BaseModel):
    id: int
    email: Optional[str]
    work_email: Optional[str]
    gender: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]
    job_title: Optional[str]
    person_address: Optional[str]
    country: Optional[str]
    personal_linkedin: Optional[str]
    seniority: Optional[str]
    departments: Optional[str]
    industries: Optional[str]
    profile_summary: Optional[str]
    points: int
    last_activity_at: Optional[str]
    last_activity_type: Optional[str]
    opted_out: bool
    opted_out_at: Optional[str]
    activities: list[LeadActivityItem] = []


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead_detail(lead_id: int, user: User = Depends(authenticate)):
    lead = await Lead.filter(id=lead_id).prefetch_related("company").first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    activities = (
        await LeadActivity.filter(lead=lead).order_by("-occurred_at").limit(20)
    )

    company = getattr(lead, "company", None)
    return LeadDetail(
        id=lead.id,  # type: ignore[arg-type]
        email=lead.email,
        work_email=lead.work_email,
        gender=lead.gender,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company_name=company.company_name if company else None,
        job_title=lead.job_title,
        person_address=lead.person_address,
        country=lead.country,
        personal_linkedin=lead.personal_linkedin,
        seniority=lead.seniority,
        departments=lead.departments,
        industries=lead.industries,
        profile_summary=lead.profile_summary,
        points=lead.points or 0,
        last_activity_at=lead.last_activity_at.isoformat() if lead.last_activity_at else None,
        last_activity_type=lead.last_activity_type,
        opted_out=bool(lead.opted_out),
        opted_out_at=lead.opted_out_at.isoformat() if lead.opted_out_at else None,
        activities=[
            LeadActivityItem(
                activity_type=activity.activity_type,
                occurred_at=activity.occurred_at.isoformat() if activity.occurred_at else None,
                metadata=activity.metadata or {},
            )
            for activity in activities
        ],
    )
