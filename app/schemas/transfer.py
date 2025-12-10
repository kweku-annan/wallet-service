from pydantic import BaseModel, Field, validator


class TransferRequest(BaseModel):
    """
    Schema for wallet-to-wallet transfer requests.
    """
    wallet_number: str = Field(..., description="Recipient's wallet number")
    amount: float = Field(..., gt=0, description="Amount to transfer (Must be greater than 0)")

    @validator('wallet_number')
    def validate_wallet_number(cls, v):
        """Validate wallet number format"""
        # Remove any spaces or dashes
        v = v.replace(' ', '').replace()

        if not v.isdigit():
            raise ValueError("Wallet number must contain only digits")

        if len(v) != 13:
            raise ValueError("Wallet number must be exactly 13 digits")

        return v

    @validator('amount')
    def validate_amount(cls, v):
        """Validate transfer amount."""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")

        if v > 10000000:  # 10 million limit
            raise ValueError("Amount exceeds maximum allowed")

        # Round to 2 decimal places
        return round(v, 2)


class TransferResponse(BaseModel):
    """
    Schema for successful transfer response.
    """
    status: str = Field(default="success", description="Transfer status")
    message: str = Field(..., description="Success message")
    amount: float
    recipient_wallet_number: str
    sender_balance: float = Field(..., description="Sender's new balance after transfer")