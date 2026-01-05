from datetime import date
from typing import Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.authenticate import authenticate
from models import Company, Lead, User

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanySummary(BaseModel):
    id: int
    company_name: str
    industry: Optional[str]
    country: Optional[str]
    company_city: Optional[str]
    company_email: Optional[str]
    company_phone: Optional[str]
    employees_amount: Optional[str]
    technologies: Optional[str]
    latest_funding: Optional[str]
    latest_funding_date: Optional[date]
    annual_revenue: Optional[str]


class CompanyLead(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    work_email: Optional[str]
    email: Optional[str]
    job_title: Optional[str]
    seniority: Optional[str]
    departments: Optional[str]


class CompanyDetail(CompanySummary):
    company_address: Optional[str]
    facebook: Optional[str]
    twitter: Optional[str]
    youtube: Optional[str]
    instagram: Optional[str]
    website: Optional[str]
    linkedin: Optional[str]
    leads: list[CompanyLead]


@router.get("", response_model=list[CompanySummary])
async def list_companies(user: User = Depends(authenticate)):
    rows = await Company.all().order_by("company_name").values(
        "id",
        "company_name",
        "company_city",
        "company_email",
        "company_phone",
        "employees_amount",
        "technologies",
        "latest_funding",
        "latest_funding_date",
        "annual_revenue",
    )
    if not rows:
        return rows
    company_ids = [row["id"] for row in rows]
    lead_rows = await Lead.filter(company_id__in=company_ids).order_by("id").values(
        "company_id",
        "industries",
        "country",
    )
    industry_map: dict[int, str] = {}
    country_map: dict[int, str] = {}
    for row in lead_rows:
        company_id = row.get("company_id")
        if company_id is None:
            continue
        industry = row.get("industries")
        if company_id not in industry_map and industry:
            industry_map[company_id] = industry
        country = row.get("country")
        if company_id not in country_map and country:
            country_map[company_id] = country
    for row in rows:
        row["industry"] = industry_map.get(row["id"])
        row["country"] = country_map.get(row["id"])
    return rows


@router.get("/{company_id}", response_model=CompanyDetail)
async def get_company(company_id: int, user: User = Depends(authenticate)):
    company = await Company.filter(id=company_id).first()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    lead_rows = await Lead.filter(company_id=company.id).values(
        "id",
        "first_name",
        "last_name",
        "work_email",
        "email",
        "job_title",
        "seniority",
        "departments",
    )
    leads = [CompanyLead(**row) for row in lead_rows]
    industry = None
    country = None
    lead_meta = await Lead.filter(company_id=company.id).order_by("id").values(
        "industries",
        "country",
    )
    for row in lead_meta:
        if industry is None and row.get("industries"):
            industry = row.get("industries")
        if country is None and row.get("country"):
            country = row.get("country")
        if industry and country:
            break
    return CompanyDetail(
        id=cast(int, company.id),
        company_name=cast(str, company.company_name),
        industry=industry,
        country=country,
        company_city=cast(Optional[str], company.company_city),
        company_email=cast(Optional[str], company.company_email),
        company_phone=cast(Optional[str], company.company_phone),
        employees_amount=cast(Optional[str], company.employees_amount),
        technologies=cast(Optional[str], company.technologies),
        latest_funding=cast(Optional[str], company.latest_funding),
        latest_funding_date=cast(Optional[date], company.latest_funding_date),
        annual_revenue=cast(Optional[str], company.annual_revenue),
        company_address=cast(Optional[str], company.company_address),
        facebook=cast(Optional[str], company.facebook),
        twitter=cast(Optional[str], company.twitter),
        youtube=cast(Optional[str], company.youtube),
        instagram=cast(Optional[str], company.instagram),
        website=getattr(company, "website", None),
        linkedin=getattr(company, "linkedin", None),
        leads=leads,
    )
