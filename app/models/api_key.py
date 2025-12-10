import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.database import Base
import secrets
import hashlib


class APIKey(Base):
    """
    API Key model for service-to-service authentication.

    Each API key:
    - Belongs to a user.
    - Has specific permissions (deposit, transfer, read)
    - Has an expiration date.
    - Can be revoked.
    - Is stored as a hash (security best practice).

    Relationships:
    - One API key belongs to one user.
    """
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)

    # Key identification
    name = Column(String, nullable=False)  # User-friendly name
    key_prefix = Column(String(8), nullable=False, index=True)  # First 8 chars of the key for identification
    key_hash = Column(String, unique=True, nullable=False, index=True) # Hashed key for security

    # Permissions (stored as JSON array: ["deposit", "transfer", "read"])
    permissions = Column(JSON, nullable=False)

    # Expiration and revocation
    expires_at = Column(DateTime, nullable=False, index=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.name} - {self.key_prefix}...>"

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure random API Key.
        :return: API key string
        """
        # Generate 32 random bytes and convert to hex (64 chars)
        random_part = secrets.token_hex(16) # 32 hex chars
        api_key = f"sk_live_{random_part}"
        return api_key

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API Key for secure storage.

        :param api_key: Plain API key
        :return: SHA256 has of the key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def parse_expiry(expiry_str: str) -> datetime:
        """
        Parse expiry string into datetime.

        Accepts 1H, 1D, 1M, 1Y
        :param expiry_str: Expiry format (e.g. "1D", "1M")
        :return: Expiration datetime
        """
        expiry_str = expiry_str.upper().strip()

        if len(expiry_str) < 2:
            raise ValueError("Invalid expiry format")

        value = expiry_str[:-1]
        unit = expiry_str[-1]

        try:
            value = int(value)
        except ValueError:
            raise ValueError("Invalid expiry value")

        now = datetime.utcnow()

        if unit == 'H':
            return now + timedelta(hours=value)
        elif unit == 'D':
            return now + timedelta(days=value)
        elif unit == 'M':
            return now + timedelta(days=value * 30)  # Approximate month as 30 days
        elif unit == 'Y':
            return now + timedelta(days=value * 365) # Approximate year as 365 days
        else:
            raise ValueError("Invalid expiry unit. Use H, D, M, or Y.")

    def is_expired(self) -> bool:
        """
        Check if the API key has expired.

        :return: True if expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at

    def has_permission(self, permission: str) -> bool:
        """
        Check if API has a specific permission.

        :param permission: Permission to check (e.g. "deposit", "transfer", "read")
        :return: True if has permission, False otherwise
        """

        return permission in self.permissions



