from fastapi import Depends, HTTPException
from .google import bearer, verify_google_token_db



async def authenticate(
    bearer_creds=Depends(bearer),
):

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

    # 2. Nothing worked → reject
    raise HTTPException(status_code=401, detail='Unauthorized')
