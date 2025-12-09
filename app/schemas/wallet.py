from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class WalletResponse(BaseModel):
    """
    Schema for wallet responses (what we send to the client).
    """
    id: str
    wallet_number: str
    balance: float
    is_active: bool
    created_at: datetime

    class Config:
        """
        Pydantic config to work with SQLAlchemy models.
        This allows us to return ORM objects directly.
        """
        from_attributes = True


class WalletBalanceResponse(BaseModel):
    """
    Schema for wallet balance response.
    """
    balance: float


class TransactionBase(BaseModel):
    """
    Base transaction schema
    """
    type: str
    amount: float
    status: str


class TransactionResponse(TransactionBase):
    """
    Schema for transaction responses (what we send to the client).
    """
    id: str
    reference: Optional[str] = None
    recipient_wallet_number: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        """
        Pydantic config to work with SQLAlchemy models.
        This allows us to return ORM objects directly.
        """
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    """
    Simplified transaction history response.
    Matches the format in the task requirements.
    """
    type: str
    amount: float
    status: str

    class Config:
        """
        Pydantic config to work with SQLAlchemy models.
        This allows us to return ORM objects directly.
        """
        from_attributes = True