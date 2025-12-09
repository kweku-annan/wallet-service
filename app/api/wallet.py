from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.middleware.auth import get_current_user
from app.services.wallet_service import WalletService
from app.schemas.wallet import WalletResponse, WalletBalanceResponse

# Create router
router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/balance", response_model=WalletBalanceResponse)
async def get_wallet_balance(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Get current user's wallet balance.

    Requires JWT authentication.

    :param current_user:
    :param db:
    :return: Wallet balance
    """
    # Get user's wallet
    wallet = WalletService.get_wallet_by_user_id(db, current_user.id)

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found for the user."
        )

    return WalletBalanceResponse(balance=wallet.balance)


@router.get("/details", response_model=WalletResponse)
async def get_wallet_details(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Get current user's wallet details including wallet number and balance.

    Requires JWT authentication.
    :param current_user:
    :param db:
    :return: Full wallet information
    """

    # Get user's wallet
    wallet = WalletService.get_wallet_by_user_id(db, current_user.id)

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found for the user."
        )

    return WalletResponse.model_validate(wallet)