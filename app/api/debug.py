from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_access_token
from typing import Optional

router = APIRouter(prefix="/debug", tags=["Debug"])

security = HTTPBearer()

@router.post("/verify-token")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Debug endpoint to verify if a JWT token can be decoded.
    This helps troubleshoot token authentication issues.
    """
    token = credentials.credentials
    
    # Try to decode
    payload = decode_access_token(token)
    
    if payload is None:
        # Try to decode without verification to see what's wrong
        from jose import jwt, JWTError
        try:
            unverified = jwt.decode(
                token, 
                options={'verify_signature': False, 'verify_exp': False}
            )
            
            # Check if expired
            from datetime import datetime
            exp = unverified.get('exp')
            is_expired = False
            if exp:
                is_expired = datetime.utcnow().timestamp() > exp
            
            return {
                "valid": False,
                "reason": "expired" if is_expired else "invalid_signature",
                "payload": unverified,
                "is_expired": is_expired,
                "hint": "Token was signed with a different SECRET_KEY or has expired"
            }
        except JWTError as e:
            return {
                "valid": False,
                "reason": "malformed",
                "error": str(e)
            }
    
    return {
        "valid": True,
        "payload": payload,
        "user_id": payload.get("user_id"),
        "email": payload.get("email")
    }


@router.get("/settings-info")
async def get_settings_info():
    """
    Get information about configured settings (without exposing secrets).
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    return {
        "algorithm": settings.ALGORITHM,
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "secret_key_length": len(settings.SECRET_KEY),
        "secret_key_first_chars": settings.SECRET_KEY[:8] + "..." if len(settings.SECRET_KEY) > 8 else "too_short",
    }
