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


@router.post("/", response_model=dict)
async def create_user(payload: UserCreate):
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
async def delete_user(payload: UserDelete):
    user = await User.get_or_none(email=payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exists")

    await user.delete()

    return {"id": user.id, "email": user.email}

@router.post("/adminize", )
async def adminize_user(payload: UserAdminize):
    user = await User.get_or_none(email=payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    if user.is_admin:
        raise HTTPException(status_code=400, detail="This guy's already been adminized")
    if user.disabled:
        raise HTTPException(status_code=400, detail="This guy's disabled")
    
    user.is_admin = True  # type: ignore[assignment]
    await user.save()
       
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin}

