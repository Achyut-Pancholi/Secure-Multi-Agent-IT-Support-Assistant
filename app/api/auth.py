from fastapi import HTTPException, Header
from typing import Optional

def verify_app_token(authorization: str = Header(None)):
    """
    Very basic Bearer token authentication for the main API.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    # In a real app, this would be a secure check. For POC, simple static token.
    if token != "poc-secret-token":
        raise HTTPException(status_code=403, detail="Forbidden")
    return token

