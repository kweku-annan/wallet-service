from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from typing import Optional


class UserService:
    """
    Service layer for user-related operations.
    Separates business logic from route handlers.
    """

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Find a user by email.
        :param db: Database session
        :param email: User's email address
        :return: User object if found, None otherwise
        """
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
        """
        Find a user by Google ID.
        :param db: Database session
        :param google_id: User's Google ID
        :return: User object if found, None otherwise
        """
        return db.query(User).filter(User.google_id == google_id).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """
        Find a user by their ID.
        :param db: Database session
        :param user_id: User's ID
        :return: User object if found, None otherwise
        """
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """
        Create a new user in the database. Also automatically creates a wallet.
        :param db: Database session
        :param user_data: User creation data
        :return: Newly created user object with wallet
        """
        from app.services.wallet_service import WalletService

        db_user = User(
            email=user_data.email,
            google_id=user_data.google_id,
            full_name=user_data.full_name,
            profile_picture=user_data.profile_picture
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user) # Refresh to get the ID and timestamps

        # Auto-create wallet for the new user
        WalletService.create_wallet_for_user(db, db_user)
        db.refresh(db_user) # Refresh again to include the wallet relationship

        return db_user

    @staticmethod
    def get_or_create_user(db: Session, user_data: UserCreate) -> tuple[User, bool]:
        """
        Get existing user or create a new one.
        :param db: Database session
        :param user_data: User data from Google OAuth
        :return:
        """
        # Try to find existing user by Google ID
        existing_user = UserService.get_user_by_google_id(db, user_data.google_id)

        if existing_user:
            return existing_user, False

        # Create new user if doesn't exist
        new_user = UserService.create_user(db, user_data)
        return new_user, True