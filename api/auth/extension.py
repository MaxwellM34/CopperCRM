from fastapi import Depends, HTTPException

from auth.google import bearer, verify_google_token_db
from config import Config
from models import User


async def get_current_user_from_google_token(
    bearer_creds=Depends(bearer),
) -> User:
    if getattr(Config, "OFFLINE_MODE", False):
        raise HTTPException(status_code=403, detail="Offline mode does not allow extension access")

    if not bearer_creds:
        raise HTTPException(status_code=401, detail="Missing token")

    token = (bearer_creds.credentials or "").strip()
    if token.lower().startswith("bearer "):
        token = token.split(None, 1)[1].strip()

    user = await verify_google_token_db(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token or user not provisioned")

    if user.disabled or not user.can_use_extension:
        raise HTTPException(status_code=403, detail="User not allowed to use extension")

    return user
