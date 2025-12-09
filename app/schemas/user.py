from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """
    Base user schema with common fileds.
    """
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """
    Schema for creating a new user (from Google OAuth).
    """
    google_id: str
    profile_picture: Optional[str] = None


class UserResponse(UserBase):
    """
    Schema for user responses (what we send to the client).
    """
    id: str
    google_id: str
    profile_picture: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        """
        Pydantic config to work with SQLAlchemy models.
        This allows us to return ORM objects directly.
        """
        from_attributes = True


class TokenResponse(BaseModel):
    """
    Schema for JWT token responses.
    """
    access_token: str
    token_type: str = "bearer"
    user: UserResponse