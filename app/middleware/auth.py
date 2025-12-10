from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Union
from app.database import get_db
from app.core.security import decode_access_token
from app.services.user_service import UserService
from app.services.api_key_service import APIKeyService
from app.models.user import User
from app.models.api_key import APIKey

# HTTP Bearer authentication scheme for Swagger UI
security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.

    :param credentials: HTTP Bearer token from Authorization header
    :param db: Database session
    :return: User object if token is valid
    :raises: HTTPException if token is invalid or user not found
    """
    # Create credentials exception
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Get token from credentials
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Extract user_id from token payload
    user_id: str = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = UserService.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_optional_user(
        authorization: Optional[str] = Header(None),
        db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Dependency to get the current user if Authorization header is provided.
    Returns None if no token provided or token is invalid

    Userful for endpoints that work with or without authentication.

    :param authorization: Authorization header optional
    :param db: Database session
    :return:
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id = payload.get("user_id")
    if user_id is None:
        return None

    user = UserService.get_user_by_id(db, user_id)
    return user if user and user.is_active else None



