from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List


class APIKeyCreateRequest(BaseModel):
    """
    Schema for creating a new API key.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the API key")
    permissions: List[str] = Field(..., min_items=1, description="List of permissions: deposit, transfer, read")
    expiry: str = Field(..., description="Expiry format: 1H, 1D, 1M, 1Y")

    @validator('permissions')
    def validate_permissions(cls, v):
        """Validate that permissions are from allowed list"""
        allowed_permissions = {"deposit", "transfer", "read"}

        for permission in v:
            if permission not in allowed_permissions:
                raise ValueError(f"Invalid permission: {permission}. Must be one of {allowed_permissions}")

        # Remove duplicates
        return list(set(v))

    @validator('expiry')
    def validate_expiry(cls, v):
        """Validate expiry format"""
        v = v.upper().strip()

        if len(v) < 2:
            raise ValueError("Invalid expiry format")

        unit = v[-1]
        if unit not in ['H', 'D', 'M', 'Y']:
            raise ValueError("Expiry unit must be H (hour), D (day), M (month), or Y (year)")

        try:
            int(v[:-1])
        except ValueError:
            raise ValueError("Expiry value must be a number")

        return v


class APIKeyCreateResponse(BaseModel):
    """
    Schema for API key creation response.

    IMPORTANT: This is the ONLY time the plain API key is returned.
    It must be saved by the client as it cannot be retrieved again.
    """
    api_key: str = Field(..., description="The API key - save this! It won't be shown again.")
    expires_at: datetime = Field(..., description="When the key expires")
    name: str
    permissions: List[str]


class APIKeyListItem(BaseModel):
    """
    Schema for listing API keys (without the actual key).
    """
    id: str
    name: str
    key_prefix: str
    permissions: List[str]
    expires_at: datetime
    is_active: bool
    is_revoked: bool
    created_at: datetime
    last_used_at: datetime | None

    class Config:
        from_attributes = True


class APIKeyRolloverRequest(BaseModel):
    """
    Schema for rolling over an expired API key.
    """
    expired_key_id: str = Field(..., description="ID of the expired key to rollover")
    expiry: str = Field(..., description="New expiry format: 1H, 1D, 1M, 1Y")

    @validator('expiry')
    def validate_expiry(cls, v):
        """Validate expiry format"""
        v = v.upper().strip()

        if len(v) < 2:
            raise ValueError("Invalid expiry format")

        unit = v[-1]
        if unit not in ['H', 'D', 'M', 'Y']:
            raise ValueError("Expiry unit must be H (hour), D (day), M (month), or Y (year)")

        try:
            int(v[:-1])
        except ValueError:
            raise ValueError("Expiry value must be a number")

        return v


class APIKeyRolloverResponse(BaseModel):
    """
    Schema for API key rollover response.
    """
    api_key: str = Field(..., description="The new API key - save this!")
    expires_at: datetime
    name: str
    permissions: List[str]
    old_key_id: str = Field(..., description="ID of the old key that was rolled over")
