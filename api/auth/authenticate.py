from fastapi import Depends, HTTPException

from .google import bearer, verify_google_token_db
from config import Config
from models import User


async def _get_offline_admin_user() -> User:
    email = getattr(Config, "OFFLINE_ADMIN_EMAIL", "devadmin@example.com")
    user, _ = await User.get_or_create(
        email=email,
        defaults={
            "firstname": "Dev",
            "lastname": "Admin",
            "is_admin": True,
            "disabled": False,
        },
    )

    needs_save = False
    if not user.is_admin:
        user.is_admin = True
        needs_save = True
    if user.disabled:
        user.disabled = False
        needs_save = True
    if needs_save:
        await user.save()
    return user


async def authenticate(
    bearer_creds=Depends(bearer),
):
    # Offline mode: skip external auth and treat the offline admin as logged in
    if getattr(Config, "OFFLINE_MODE", False):
        return await _get_offline_admin_user()

    # 1 Try Google
    if bearer_creds:
        token = (bearer_creds.credentials or "").strip()
        if token.lower().startswith("bearer "):
            token = token.split(None, 1)[1].strip()

        user = await verify_google_token_db(token)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid token or user not provisioned")
        elif user and not user.disabled:
            # TODO: Log Google auth usage
            return user

    # 2. Nothing worked; reject
    raise HTTPException(status_code=401, detail="Unauthorized")
