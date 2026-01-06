from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from auth.authenticate import authenticate, get_google_email
from models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=dict)
async def get_current_user(user: User = Depends(authenticate)):
    """
    Simple authenticated endpoint used by the UI to validate the token and fetch user info.
    Only returns when the user exists and is not disabled.
    """
    return {
        "id": user.id,
        "email": user.email,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "is_admin": user.is_admin,
        "disabled": user.disabled,
    }


@router.get("/verify", response_model=dict)
async def verify_user(email: str = Depends(get_google_email)):
    user = await User.get_or_none(email__iexact=email)
    if not user or user.disabled:
        return JSONResponse(status_code=403, content={"authorized": False})
    return {"email": user.email, "authorized": True}
