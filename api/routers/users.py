from fastapi import APIRouter, HTTPException, Depends
from auth.authenticate import authenticate
from pydantic import BaseModel
from models import User

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    firstname: str
    lastname: str | None = None

class UserDelete(BaseModel):
    email: str

class UserAdminize(BaseModel):
    email: str


## Create / Delete

@router.post("/", response_model=dict)
async def create_user(payload: UserCreate, user: User = Depends(authenticate)):
    existing = await User.get_or_none(email=payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = await User.create(
        email=payload.email,
        firstname=payload.firstname,
        lastname=payload.lastname,
    )

    return {"id": user.id, "email": user.email}

@router.delete("/delete user", response_model=dict)
async def deleteuser(payload: UserDelete, user: User = Depends(authenticate)):
    if not await User.filter(email=payload.email).exists():
        raise HTTPException(status_code=404, detail="User not found")

    await user.delete()

    return {"id": user.id, "email": user.email}


## Permissions


@router.post("/adminize", response_model=dict)
async def adminize_user(
    payload: UserAdminize,
    current_user: User = Depends(authenticate),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")

    target_user = await User.get_or_none(email=payload.email)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.is_admin:
        raise HTTPException(status_code=409, detail="User is already admin")
    if target_user.disabled:
        raise HTTPException(status_code=400, detail="User is disabled")

    target_user.is_admin = True  # type: ignore[assignment]  # (optional for Pylance)
    await target_user.save()

    return {"id": target_user.id, "email": target_user.email, "is_admin": target_user.is_admin}

@router.post("/deadminize", response_model=dict)
async def deadminize_user(
    payload: UserAdminize,
    current_user: User = Depends(authenticate),
):
    # Only admins can deadminize
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")

    target_user = await User.get_or_none(email=payload.email)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-demotion (optional but strongly recommended)
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deadminize yourself")

    if not target_user.is_admin:
        raise HTTPException(status_code=409, detail="User is not an admin")

    target_user.is_admin = False  # type: ignore[assignment]
    await target_user.save()

    return {
        "id": target_user.id,
        "email": target_user.email,
        "is_admin": target_user.is_admin,
    }
