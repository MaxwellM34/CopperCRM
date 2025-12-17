from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from auth.authenticate import authenticate
from models import Lead, User

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadDisplay(BaseModel):
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
