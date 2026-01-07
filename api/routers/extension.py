from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from auth.authenticate import authenticate
from models import User
from services.linkedin_lookup import find_lead_by_linkedin, lead_to_profile

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
