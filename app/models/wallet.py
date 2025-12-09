import uuid

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import secrets


class Wallet(Base):
    """
    Wallet model - each user has one wallet.

    The wallet holds the user's balance and has a unique wallet number
    for receiving transfers from other users.

    Relationships:
    - One wallet belongs to one user.
    - One wallet can have many transactions.
    """
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), unique=True, nullable=False)
    wallet_number = Column(String, unique=True, index=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")

    def __repr__(self):
        return f"<Wallet {self.wallet_number} - Balance: {self.balance}"

    @staticmethod
    def generate_wallet_number() -> str:
        """
        Generate a unique 13-digit wallet number.

        Format: XXXX-XXXX-XXXXX (without dashes in storage)
        Example: 4566678954356

        :return: 13-digit wallet number as string
        """
        # Generate 13 random digits
        wallet_number = ''.join([str(secrets.randbelow(10)) for _ in range(13)])
        return wallet_number
