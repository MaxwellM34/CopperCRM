from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import User

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    firstname: str
    lastname: str | None = None


@router.post("", response_model=dict)
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
