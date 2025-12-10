from sqlalchemy.orm import Session
from app.models.api_key import APIKey
from app.models.user import User
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from datetime import datetime


class APIKeyService:
    """
    Service layer for API key operations.
    """

    @staticmethod
    def get_active_key_count(db: Session, user_id: str) -> int:
        """
        Count active (non-revoked, non-expired) API keys for a user.
        :param db:
        :param user_id:
        :return: Count of active API keys
        """
        now = datetime.utcnow()
        count = db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.is_revoked == False,
            APIKey.expires_at > now
        ).count()

        return count

    @staticmethod
    def create_api_key(
            db: Session,
            user: User,
            name: str,
            permissions: List[str],
            expiry: str
    ) -> Tuple[APIKey, str]:
        """
        Create a new API key for a user.

        :param db: Database session
        :param user: User object
        :param name: Friendly name for the API key
        :param permissions: List of permissions
        :param expiry: Expiry string (e.g. "1D", "1M")
        :return: Tuple of (APIKey object, plain API key string)
        :raises: HTTPException if user has too many keys or invalid data
        """
        # Check if user has reached the limit
        active_count = APIKeyService.get_active_key_count(db, user.id)
        if active_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum of 5 active API keys allowed. Revoke existing keys to create new ones."
            )
        # Generate API key
        plain_key = APIKey.generate_api_key()
        key_hash = APIKey.hash_api_key(plain_key)
        key_prefix = plain_key[:8]  # "sk_live_"

        # Parse expiry
        try:
            expires_at = APIKey.parse_expiry(expiry)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Create API key record
        api_key = APIKey(
            user_id=user.id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            permissions=permissions,
            expires_at=expires_at
        )

        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        # Return both the database record and the plain key
        # IMPORTANT: This is the only time we return the plain key
        return api_key, plain_key

    @staticmethod
    def verify_api_key(db: Session, api_key: str) -> Optional[APIKey]:
        """
        Verify an API key and return the corresponding APIKey object if valid.

        :param db: Database session
        :param api_key: Plain API key string
        :return: APIKey object if valid, None otherwise
        """
        key_hash = APIKey.hash_api_key(api_key)

        # Find the key
        db_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

        if not db_key:
            return None

        # Check if key is revoked
        if db_key.is_revoked or not db_key.is_active:
            return None

        # Check if key is expired
        if db_key.is_expired():
            return None

        # Update last used timestamp
        db_key.last_used_at = datetime.utcnow()
        db.commit()

        return db_key


    @staticmethod
    def get_user_api_keys(db: Session, user_id: str) -> List[APIKey]:
        """
        Get all API keys for a user
        :param db: Database Session
        :param user_id: User's ID
        :return: List of APIKey objects
        """
        return db.query(APIKey).filter(APIKey.user_id == user_id).order_by(APIKey.created_at.desc()).all()

    @staticmethod
    def get_api_key_by_id(db: Session, key_id: str, user_id: str) -> Optional[APIKey]:
        """
        Get an API key by ID, ensuring it belongs to the user.
        :param db: Database session
        :param key_id: API key ID
        :param user_id: user's ID
        :return: APIKey object if found and belongs to user, None otherwise
        """
        return db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()

    @staticmethod
    def revoke_api_key(db: Session, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key by setting is_revoked to True.
        :param db: Database session
        :param key_id: API key ID
        :param user_id: User's ID
        :return: True if successfully revoked, False otherwise
        """
        api_key = APIKeyService.get_api_key_by_id(db, key_id, user_id)
        if not api_key:
            return False

        api_key.is_revoked = True
        api_key.is_active = False
        db.commit()

        return True

    @staticmethod
    def rollover_api_key(
            db: Session,
            expired_key_id: str,
            user: User,
            new_expiry: str
    ) -> Tuple[APIKey, str]:
        """
        Create a new API key using permissions from an expired key

        :param db: Database session
        :param expired_key_id: ID of the expired key to rollover
        :param user: User object
        :param new_expiry: New expiry string
        :return: Tuple of (new APIKey object, plain API key string)
        :raises: HTTPException if the expired key is invalid, not found, or other errors
        """
        # Get the old key
        old_key = APIKeyService.get_api_key_by_id(db, expired_key_id, user.id)

        if not old_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expired API key not found."
            )

        # Check if the key is actually expired
        if not old_key.is_expired():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The specified API key is not expired."
            )

        # Revoke the old key
        old_key.is_revoked = True
        old_key.is_active = False

        # Create a new key with same permissions
        new_key, plain_key = APIKeyService.create_api_key(
            db=db,
            user=user,
            name=old_key.name,
            permissions=old_key.permissions,
            expiry=new_expiry
        )

        db.commit()

        return new_key, plain_key









