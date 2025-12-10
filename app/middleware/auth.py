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

async def get_current_user_or_api_key(
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None),
        db: Session = Depends(get_db),
) -> tuple[User, Optional[APIKey]]:
    """
    Dependency that accepts EITHER JWT token OR API key.

    This is used for wallet endpoints that support both authentication methods.

    Priority:
    1. If Authorization header exists -> validate JWT
    2. If x-api-key header exists -> validate API key
    3. If neither exists or both invalid -> raise 401 Unauthorized

    :param authorization: Authorization Bearer token (optional)
    :param x_api_key: API key header (optional)
    :param db: Database Session
    :return: Tuple of (User object, APIKey object or None)
    :raises HTTPException if both auth methods fail or neither provided
    """
    # Try JWT first
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)

        if payload:
            user_id: str = payload.get("user_id")
            if user_id:
                user = UserService.get_user_by_id(db, user_id)
                if user and user.is_active:
                    return user, None

    # Try API key
    if x_api_key:
        api_key = APIKeyService.verify_api_key(db, x_api_key)

        if api_key:
            user = UserService.get_user_by_id(db, api_key.user_id)
            if user and user.is_active:
                return user, api_key

        # API key provided but invalid
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide either JWT token or API key."
        )

def require_permission(
        permission: str
    ):
    """
    Decorator factory to require specific permission for API key access.

    :param permission: Permission string required (e.g. "deposit", "transfer", "read"
    :return: Dependency function that validates permission
    """
    async def permission_checker(
            auth_data: tuple = Depends(get_current_user_or_api_key)
    ) -> User:
        user, api_key = auth_data

        # If using JWT, all permissions are granted
        if api_key is None:
            return

        # If using API key, check permissions
        if not api_key.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have required permission: {permission}"
            )

        return

    return permission_checker



