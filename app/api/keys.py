from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.middleware.auth import get_current_user
from app.services.api_key_service import APIKeyService
from app.schemas.api_key import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListItem,
    APIKeyRolloverRequest,
    APIKeyRolloverResponse
)
from typing import List

# Create router
router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("/create", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
        request: APIKeyCreateRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Create a new API key for service-to-service authentication.

    Rules:
    - Maximum of 5 active keys per user.
    - Permissions: deposit, transfer, read.
    - Expiration: 1H, 1D, 1M, 1Y

    IMPORTANT: Save the returned API key securely as it will not be shown again.

    :param request:
    :param current_user:
    :param db:
    :return: API key (only shown once) and expiration time
    """
    # Create the API key
    api_key_obj, plain_key = APIKeyService.create_api_key(
        db=db,
        user=current_user,
        name=request.name,
        permissions=request.permissions,
        expiry=request.expiry
    )

    return APIKeyCreateResponse(
        api_key=plain_key,
        expires_at=api_key_obj.expires_at,
        name=api_key_obj.name,
        permissions=api_key_obj.permissions
    )


@router.get("/list", response_model=List[APIKeyListItem])
async def list_api_keys(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    List all API keys for the current user.

    Note: The actual API key values are NOT returned for security reasons.
    Only metadata like name, prefix, permissions, and expiry are shown.
    :param current_user:
    :param db:
    :return: List of API Key metadata
    """
    keys = APIKeyService.get_user_api_keys(db, current_user.id)
    return [APIKeyListItem.model_validate(key) for key in keys]


@router.post("/rollover", response_model=APIKeyRolloverResponse)
async def rollover_api_key(
        request: APIKeyRolloverRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Rollover an expired API key to create a new one with the same permissions.

    Rules:
    - The old key MUST be expired.
    - The new key inherits all permissions from the old key.
    - The old key is revoked after rollover.
    :param request:
    :param current_user:
    :param db:
    :return: New API key (only shown once) and expiration time
    """
    try:
        expired_key_id = request.expired_key_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format."
        )

    # Rollover the key
    new_key, plain_key = APIKeyService.rollover_api_key(
        db=db,
        expired_key_id=expired_key_id,
        user=current_user,
        new_expiry=request.expiry
    )

    return APIKeyRolloverResponse(
        api_key=plain_key,
        expires_at=new_key.expires_at,
        name=new_key.name,
        permissions=new_key.permissions,
        old_key_id=expired_key_id
    )


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def revoke_api_key(
        key_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Revoke an API key by its ID.

    :param key_id:
    :param current_user:
    :param db:
    :return: Success message
    """
    success = APIKeyService.revoke_api_key(db, key_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found."
        )

    return {"message": "API key revoked successfully", "key_id": key_id}