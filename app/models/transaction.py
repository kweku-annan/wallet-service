import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class TransactionType(str, enum.Enum):
    """
    Enum for transaction types.
    """
    DEPOSIT = 'deposit'
    TRANSFER = 'transfer'
    WITHDRAWAL = 'withdrawal'


class TransactionStatus(str, enum.Enum):
    """
    Enum for transaction status.
    """
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'


class Transaction(Base):
    """
    Transaction model - records all wallet transactions.

    Tracks deposits from Paystack, transfers between users, and other operations.
    Each transaction is linked to a wallet and a user.

    For transfers:
    - The sender's wallet creates a transaction with type=TRANSFER (debit)
    - The recipient's wallet creates a transaction with type=DEPOSIT (credit)

    For Paystack deposits:
    - A transaction with type=DEPOSIT is created upon successful payment and reference from Paystack.
    """
    __tablename__ = 'transactions'

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    wallet_id = Column(String(36), ForeignKey('wallets.id'), nullable=False)

    # Transaction details
    type = Column(SQLEnum(TransactionType), nullable=False)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    amount = Column(Float, nullable=False)

    # Reference for Paystack transactions (unique payment reference)
    reference = Column(String, unique=True, nullable=True, index=True)

    # For transfers: recipient wallet number
    recipient_wallet_number = Column(String, nullable=True)

    # Description/metadata
    description = Column(String, nullable=True)
    transaction_metadata = Column(String, nullable=True)  # JSON string for additional data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='transactions')
    wallet = relationship('Wallet', back_populates='transactions')

    def __repr__(self):
        return f"<Transaction {self.type.value} - {self.amount} - {self.status.value}>"
