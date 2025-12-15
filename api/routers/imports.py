from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from models import User, Lead
from auth.authenticate import authenticate
from datetime import datetime, date
import os
from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix='', tags=['leads'])

class LeadImportRow(BaseModel):
    id: int
    email: str
    work_email: str
    first_name: str
    last_name: str
    job_title: str | None
    company_id: int | None
    work_email_status: str | None
    work_email_quality: str | None
    work_email_confidence: str | None
    primary_work_email_source: str | None
    work_email_service_provider: str | None
    catch_all_status: bool | None
    person_address: str | None
    country: str | None
    personal_linkedin: str | None
    seniority: str | None
    departments: str | None
    industries: str | None
    profile_summary: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CompanyImportRow(BaseModel):
    company_name: str | None = None
    employees_amount: str | None = None
    company_address: str | None = None
    company_city: str | None = None
    company_phone: str | None = None
    company_email: str | None = None
    technologies: str | None = None
    latest_funding: str | None = None
    lastest_funding_date: date | None = None
    facebook: str | None = None
    twitter: str | None = None
    youtube: str | None = None
    instagram: str | None = None
    annual_revenue: str | None = None

class ImportRowError(BaseModel):
    row_number: int
    message: str
    raw: dict = Field(default_factory=dict)

class LeadCompanyImportResult(BaseModel):
    companies_created: int = 0
    companies_updated: int = 0
    leads_created: int = 0
    leads_updated: int = 0
    skipped: int = 0
    errors: list[ImportRowError] = Field(default_factory=list)

@router.post("/import")
async def import_leads_csv(file: UploadFile = File(...), user=Depends(authenticate)):
    pass
