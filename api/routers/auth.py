from fastapi import APIRouter, Depends
from auth.authenticate import authenticate
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
