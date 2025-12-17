from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from models import User, Lead, Company
from auth.authenticate import authenticate
from datetime import date
from fastapi import HTTPException, Query
from pydantic import BaseModel, Field
import io
import csv

from services.gender_infer import infer_gender_by_name

router = APIRouter(prefix='/leads', tags=['leads'])

# Classes are missing db exclusive fields

class LeadImportRow(BaseModel):
    email: str | None
    work_email: str | None
    first_name: str | None
    last_name: str | None
    job_title: str | None
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


def _s(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() != "nan" else None

def _b(v):
    s = _s(v)
    if s is None:
        return None
    s = s.lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False
    return None
def _d(v):
    s = _s(v)
    if not s:
        return None
    try:
        return date.fromisoformat(s)  # expects YYYY-MM-DD
    except Exception:
        return None

def _set_if_present(obj, field: str, value):
    if value is not None:
        setattr(obj, field, value)



@router.post("/import", response_model=LeadCompanyImportResult)
async def importLeadsCSV(file: UploadFile = File(...), user: User = Depends(authenticate)):
    try:    
        if not file.filename:
            raise HTTPException(status_code=400, detail="Missing filename")
    
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Use a CSV Dummy")
        
        text = (await file.read()).decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))

        if not reader.fieldnames:
                raise HTTPException(status_code=400, detail='CSV Missing Headers')
        
        result = LeadCompanyImportResult()
        row_number = 1

        for row in reader:
            row_number += 1


            try:
                # --- Parse Waste Water CSV columns ---
                lead_row = LeadImportRow(
                    work_email=_s(row.get("Work Email")),
                    email=_s(row.get("Personal Email")),
                    first_name=_s(row.get("First Name")),
                    last_name=_s(row.get("Last Name")),
                    job_title=_s(row.get("Job Title")),
                    work_email_status=_s(row.get("Work Email Status")),
                    work_email_quality=_s(row.get("Work Email Quality")),
                    work_email_confidence=_s(row.get("Work Email Confidence")),
                    primary_work_email_source=_s(row.get("Primary Work Email Source")),
                    work_email_service_provider=_s(row.get("Work Email Service Provider")),
                    catch_all_status=_b(row.get("Catch-all Status")),
                    person_address=_s(row.get("Person Address")),
                    country=_s(row.get("Country")),
                    personal_linkedin=_s(row.get("Personal LinkedIn")),
                    seniority=_s(row.get("Seniority")),
                    departments=_s(row.get("Departments")),
                    industries=_s(row.get("Industries")),
                    profile_summary=_s(row.get("Profile Summary")),
                )

                company_row = CompanyImportRow(
                    company_name=_s(row.get("Company")),
                    employees_amount=_s(row.get("# Employees")),
                    company_address=_s(row.get("Company Address")),
                    company_city=_s(row.get("Company City")),
                    company_phone=_s(row.get("Company Phone")) or _s(row.get("Phone")),
                    company_email=_s(row.get("Company Email")),
                    technologies=_s(row.get("Technologies")),
                    latest_funding=_s(row.get("Latest Funding")),
                    lastest_funding_date=_d(row.get("Last Raised At")),
                    facebook=_s(row.get("Facebook")),
                    twitter=_s(row.get("Twitter")),
                    youtube=_s(row.get("Youtube")),
                    instagram=_s(row.get("Instagram")),
                    annual_revenue=_s(row.get("Annual Revenue")),
                )       

# Per-row required fields: fail-fast with HTTP 400
                if not (lead_row.work_email or lead_row.email):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Row {row_number}: missing Work Email and Personal Email",
                    )
                if not lead_row.first_name:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Row {row_number}: missing First Name",
                    )
                if not company_row.company_name:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Row {row_number}: missing Company",
                    )

                # Upsert Company
                company_obj = await Company.get_or_none(company_name=company_row.company_name)
                if company_obj:
                    _set_if_present(company_obj, "employees_amount", company_row.employees_amount)
                    _set_if_present(company_obj, "company_address", company_row.company_address)
                    _set_if_present(company_obj, "company_city", company_row.company_city)
                    _set_if_present(company_obj, "company_phone", company_row.company_phone)
                    _set_if_present(company_obj, "company_email", company_row.company_email)
                    _set_if_present(company_obj, "technologies", company_row.technologies)
                    _set_if_present(company_obj, "latest_funding", company_row.latest_funding)
                    _set_if_present(company_obj, "lastest_funding_date", company_row.lastest_funding_date)
                    _set_if_present(company_obj, "facebook", company_row.facebook)
                    _set_if_present(company_obj, "twitter", company_row.twitter)
                    _set_if_present(company_obj, "youtube", company_row.youtube)
                    _set_if_present(company_obj, "instagram", company_row.instagram)
                    _set_if_present(company_obj, "annual_revenue", company_row.annual_revenue)
                    company_obj.updated_by = user
                    await company_obj.save()
                    result.companies_updated += 1
                else:
                    company_obj = await Company.create(
                        company_name=company_row.company_name,
                        employees_amount=company_row.employees_amount,
                        company_address=company_row.company_address,
                        company_city=company_row.company_city,
                        company_phone=company_row.company_phone,
                        company_email=company_row.company_email,
                        technologies=company_row.technologies,
                        latest_funding=company_row.latest_funding,
                        lastest_funding_date=company_row.lastest_funding_date,
                        facebook=company_row.facebook,
                        twitter=company_row.twitter,
                        youtube=company_row.youtube,
                        instagram=company_row.instagram,
                        annual_revenue=company_row.annual_revenue,
                        created_by=user,
                        updated_by=user,
                    )
                    result.companies_created += 1

                # Upsert Lead (prefer work_email)
                lead_obj = None
                if lead_row.work_email:
                    lead_obj = await Lead.get_or_none(work_email=lead_row.work_email)
                if not lead_obj and lead_row.email:
                    lead_obj = await Lead.get_or_none(email=lead_row.email)

                if lead_obj:
                    for k, v in lead_row.model_dump().items():
                        if v is not None:
                            setattr(lead_obj, k, v)
                    lead_obj.company = company_obj
                    if lead_row.first_name:
                        lead_obj.gender = infer_gender_by_name(lead_row.first_name)
                    lead_obj.updated_by = user
                    await lead_obj.save()
                    result.leads_updated += 1
                else:
                    gender = infer_gender_by_name(lead_row.first_name)
                    await Lead.create(
                        **lead_row.model_dump(),
                        company=company_obj,
                        gender=gender,
                        created_by=user,
                        updated_by=user,
                    )
                    result.leads_created += 1

            except HTTPException:
                raise
            except Exception as e:
                result.skipped += 1
                result.errors.append(
                    ImportRowError(row_number=row_number, message=str(e), raw=row)
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
