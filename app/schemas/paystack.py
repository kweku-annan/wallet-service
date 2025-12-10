from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any


class DepositRequest(BaseModel):
    """
    Schema for initiating a Paystack deposit.
    """
    amount: float = Field(..., gt=0, description="Amount to deposit in NGN (Must be greater than 0)")

    @validator('amount')
    def validate_amount(cls, v):
        """Ensure amount is positive and reasonable"""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        if v > 10000000: # 10 million NGN limit for single deposit
            raise ValueError("Amount exceeds maximum limit of 10,000,000 NGN")
        return round(v, 2) # Round to 2 decimal places


class DepositResponse(BaseModel):
    """
    Schema for deposit initialization response from Paystack.
    """
    reference: str = Field(..., description="Unique reference for the deposit transaction")
    authorization_url: str = Field(..., description="URL to redirect user for payment authorization")
    amount: float


class DepositStatusResponse(BaseModel):
    """
    Schema for deposit status response from Paystack.
    """
    reference: str
    status: str = Field(..., description="Status of the deposit transaction (e.g., success, failed)")
    amount: float


class PaystackWebhookEvent(BaseModel):
    """
    Schema for Paystack webhook event payload.

    Paystack sends this when a transaction status changes.
    """
    event: str = Field(..., description="Type of event (e.g., charge.success)")
    data: Dict[str, Any] = Field(..., description="Event data payload containing transaction details")


class PaystackChargeData(BaseModel):
    """
    Schema for the 'data' field in charge.success webhook event
    """
    reference: str
    amount: int  # Amount in kob (Paystack uses smallet currency unit)
    status: str
    customer: Optional[Dict[str, Any]] = None
    paystack_metadata: Optional[Dict[str, Any]] = None
