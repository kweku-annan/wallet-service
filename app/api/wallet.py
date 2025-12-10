from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.models.transaction import TransactionType, TransactionStatus
from app.middleware.auth import get_current_user, get_current_user_or_api_key_swagger, require_permission
from app.services.paystack_service import PaystackService
from app.services.wallet_service import WalletService
from app.schemas.wallet import (
    WalletResponse,
    WalletBalanceResponse,
    TransactionHistoryResponse
)
from app.schemas.paystack import (
    DepositRequest,
    DepositResponse,
    DepositStatusResponse,
    PaystackWebhookEvent
)
from app.schemas.transfer import TransferRequest, TransferResponse
from typing import List, Tuple

# Create router
router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/balance", response_model=WalletBalanceResponse)
async def get_wallet_balance(
        auth_data: Tuple[User, APIKey | None] = Depends(get_current_user_or_api_key_swagger),
        _: None = Depends(require_permission("read")),
        db: Session = Depends(get_db),
):
    """
     Get current user's wallet balance.

    Requires:
    - JWT authentication OR
    - API key with 'read' permission

    Returns:
        Wallet balance
    """
    user, api_key = auth_data
    # Get user's wallet
    wallet = WalletService.get_wallet_by_user_id(db, user.id)

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

    Requires JWT authentication. (not available via API Key for security reasons)
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

@router.post("/deposit", response_model=DepositResponse, status_code=status.HTTP_201_CREATED)
async def initiate_deposit(
        request: DepositRequest,
        auth_data: Tuple[User, APIKey | None] = Depends(get_current_user_or_api_key_swagger),
        _: None = Depends(require_permission("deposit")),
        db: Session = Depends(get_db),
):
    """
    Initialize a wallet deposit using Paystack.

    Flow:
    1. User requests a deposit with an amount.
    2. Server initializes Paystack transaction.
    3. Server returns Paystack payment URL.
    4. User completes payment on Paystack.
    5. Paystack sends webhook to credit wallet.

    Requires:
    - JWT authentication OR
    - API key with 'deposit' permission

    :param request:
    :param auth_data:
    :param _:
    :param db:
    :return: Payment reference and Paystack authorization URL
    """
    user, api_key = auth_data

    # Get or create wallet
    wallet = WalletService.get_or_create_wallet(db, user)

    # Initialize Paystack transaction
    reference, authorization_url = PaystackService.initialize_transaction(
        email=user.email,
        amount=request.amount
    )

    # Create transaction record (status: pending)
    WalletService.create_transaction(
        db=db,
        user_id=user.id,
        wallet_id=wallet.id,
        amount=request.amount,
        transaction_status=TransactionStatus.PENDING,
        reference=reference,
        description=f"Deposit via Paystack",
        transaction_type=TransactionType.DEPOSIT,
    )

    return DepositResponse(
        reference=reference,
        authorization_url=authorization_url,
        amount=request.amount,
    )

@router.post("/paystack/webhook", status_code=status.HTTP_200_OK)
async def paystack_webhook(
        request: Request,
        db: Session = Depends(get_db),
):
    """
    Paystack webhook endpoint.

    CRITICAL: This endpoint:
    - Receives transaction updates from Paystack.
    - Verifies webhook signature for security.
    - Credits wallet ONLY after successful payment.
    - Is idempotent (no double-crediting).

    Security:
    - Validates Paystack signature using HMAC SHA512
    - Only processes 'charge.success' events.
    - Ensures transaction reference is unique.

    :param request:
    :param db:
    :return:
    """
    # Get raw body and signature
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    # Verify webhook signature
    if not PaystackService.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Paystack webhook signature."
        )
    # Parse webhook payload
    try:
        import json
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload."
        )
    # Only process successful charge events
    event = payload.get("event")
    if event != "charge.success":
        # Acknowledge other events but don't process them
        return {"status": True, "message": f"Event '{event} acknowledged but not processed."}

    # Extract transaction data
    data = payload.get("data", {})
    reference = data.get("reference")
    amount_in_kobo = data.get("amount", 0)
    paystack_status = data.get("status")

    if not reference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing transaction reference."
        )

    # Convert amount from kobo to Naira
    amount = PaystackService.kobo_to_naira(amount_in_kobo)

    # Find transaction in database
    transaction = WalletService.get_transaction_by_reference(db, reference)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction not found: {reference}"
        )

    # IDEMPOTENCY CHECK: Don't credit twice
    if transaction.status == TransactionStatus.SUCCESS:
        # Transaction already processed
        return {
            "status": True,
            "message": f"Transaction {reference} already processed."
        }

    # Verify if amounts match
    if transaction.amount != amount:
        transaction.status = TransactionStatus.FAILED
        transaction.description = f"Amount mismatch: expected {transaction.amount}, got {amount}"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction amount mismatch."
        )

    # Update transaction status based on Paystack status
    if paystack_status == "success":
        # Credit wallet
        wallet = WalletService.get_wallet_by_user_id(db, transaction.user_id)

        if not wallet:
            raise  HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found for the user."
            )

        # Add funds to wallet
        WalletService.update_balance(db, wallet, amount, operation="add")

        # Update transaction status
        transaction.status = TransactionStatus.SUCCESS
        db.commit()

        return {
            "status": True,
            "message": f"Wallet credited: {amount} NGN"
        }
    else:
        # Transaction failed
        transaction.status = TransactionStatus.FAILED
        db.commit()

        return {
            "status": True,
            "message": "Transaction failed"
        }

@router.get("/paystack/callback", response_class=HTMLResponse)
async def paystack_callback(
        reference: str = Query(..., description="Payment reference"),
        db: Session = Depends(get_db),
):
    """
    Paystack payment callback endpoint.
    
    This endpoint is called by Paystack after a user completes payment.
    It provides immediate feedback to the user about their payment status.
    
    Flow:
    1. User completes payment on Paystack
    2. Paystack redirects to this endpoint with reference
    3. We verify the transaction with Paystack API
    4. Update transaction status if webhook hasn't processed it yet
    5. Display user-friendly success/failure message
    
    Note: The webhook is the primary mechanism for crediting wallets.
    This callback serves as a backup and provides user feedback.
    
    :param reference: Transaction reference from Paystack
    :param db: Database session
    :return: HTML response with payment status
    """
    try:
        # Find transaction in database
        transaction = WalletService.get_transaction_by_reference(db, reference)
        
        if not transaction:
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Payment Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: #d32f2f; }}
                </style>
            </head>
            <body>
                <h1 class="error">Transaction Not Found</h1>
                <p>Invalid payment reference: {reference}</p>
            </body>
            </html>
            """
        
        # Check if already processed
        if transaction.status == TransactionStatus.SUCCESS:
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Payment Success</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: #388e3c; }}
                </style>
            </head>
            <body>
                <h1 class="success">✓ Payment Successful!</h1>
                <p>Amount: ₦{transaction.amount:,.2f}</p>
                <p>Reference: {transaction.reference}</p>
                <p>Your wallet has been credited.</p>
            </body>
            </html>
            """
        
        # Verify transaction with Paystack
        try:
            paystack_data = PaystackService.verify_transaction(reference)
            paystack_status = paystack_data.get("status")
            amount_in_kobo = paystack_data.get("amount", 0)
            amount = PaystackService.kobo_to_naira(amount_in_kobo)
            
            # Verify amounts match
            if transaction.amount != amount:
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"Amount mismatch: expected {transaction.amount}, got {amount}"
                db.commit()
                
                return f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Payment Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .error {{ color: #d32f2f; }}
                    </style>
                </head>
                <body>
                    <h1 class="error">✗ Payment Failed</h1>
                    <p>Transaction amount mismatch.</p>
                    <p>Reference: {reference}</p>
                </body>
                </html>
                """
            
            # Update transaction based on Paystack status
            if paystack_status == "success":
                # Credit wallet (idempotent - only if not already successful)
                wallet = WalletService.get_wallet_by_user_id(db, transaction.user_id)
                
                if wallet:
                    WalletService.update_balance(db, wallet, amount, operation="add")
                    transaction.status = TransactionStatus.SUCCESS
                    db.commit()
                    
                    return f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Payment Success</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                            .success {{ color: #388e3c; }}
                        </style>
                    </head>
                    <body>
                        <h1 class="success">✓ Payment Successful!</h1>
                        <p>Amount: ₦{amount:,.2f}</p>
                        <p>Reference: {reference}</p>
                        <p>Your wallet has been credited.</p>
                    </body>
                    </html>
                    """
                else:
                    return f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Payment Error</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                            .error {{ color: #d32f2f; }}
                        </style>
                    </head>
                    <body>
                        <h1 class="error">✗ Error</h1>
                        <p>Wallet not found.</p>
                        <p>Please contact support with reference: {reference}</p>
                    </body>
                    </html>
                    """
            else:
                # Payment failed
                transaction.status = TransactionStatus.FAILED
                db.commit()
                
                return f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Payment Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .error {{ color: #d32f2f; }}
                    </style>
                </head>
                <body>
                    <h1 class="error">✗ Payment Failed</h1>
                    <p>Your payment was not successful.</p>
                    <p>Reference: {reference}</p>
                </body>
                </html>
                """
                
        except HTTPException as e:
            # Paystack verification failed
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Payment Verification Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: #d32f2f; }}
                </style>
            </head>
            <body>
                <h1 class="error">✗ Verification Error</h1>
                <p>Unable to verify payment with Paystack.</p>
                <p>Reference: {reference}</p>
                <p>Please check your wallet balance or contact support.</p>
            </body>
            </html>
            """
            
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <h1 class="error">✗ Error</h1>
            <p>An unexpected error occurred.</p>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """


@router.get("/deposit/{reference}/status", response_model=DepositStatusResponse)
async def check_deposit_status(
        reference: str,
        auth_data: Tuple[User, APIKey | None] = Depends(get_current_user_or_api_key_swagger),
        _: None = Depends(require_permission("read")),
        db: Session = Depends(get_db),
):
    """
    Check the status of a deposit transaction by its reference.

    This is manual check endpoint - it does NOT credit wallets.
    Only the webhook endpoint credits wallets.

    Requires:
    - JWT authentication OR
    - API key with 'read' permission
    :param reference:
    :param auth_data:
    :param _:
    :param db:
    :return: Transaction status (pending, success, failed)
    """
    user, api_key = auth_data

    # Find transaction
    transaction = WalletService.get_transaction_by_reference(db, reference)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction not found: {reference}"
        )

    # Verify transaction belongs to user
    if transaction.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this transaction."
        )

    return DepositStatusResponse(
        reference=transaction.reference,
        status=transaction.status.value,
        amount=transaction.amount
    )


@router.get("/transactions", response_model=List[TransactionHistoryResponse])
async def get_transaction_history(
        auth_data: Tuple[User, APIKey | None] = Depends(get_current_user_or_api_key_swagger),
        _: None = Depends(require_permission("read")),
        db: Session = Depends(get_db),
        limit: int = 50,
        offset: int = 0
):
    """
    Get user's transaction history.

    Requires:
    - JWT authentication OR
    - API key with 'read' permission

    Query Parameters:
    - limit: Maximum number of transactions (default: 50)
    - offset: Number of transactions to skip (default: 0)

    Returns:
        List of transactions with type, amount, and status
    """
    user, api_key = auth_data

    # Get transactions
    transactions = WalletService.get_user_transaction(
        db=db,
        user_id=user.id,
        limit=limit,
        offset=offset
    )

    return [
        TransactionHistoryResponse(
            type=txn.type.value,
            amount=txn.amount,
            status=txn.status.value
        )
        for txn in transactions
    ]


@router.post("/transfer", response_model=TransferResponse, status_code=status.HTTP_200_OK)
async def transfer_funds(
        request: TransferRequest,
        auth_data: Tuple[User, APIKey | None] = Depends(get_current_user_or_api_key_swagger),
        _: None = Depends(require_permission("transfer")),
        db: Session = Depends(get_db)
):
    """
    Transfer funds from your wallet to another user's wallet.

    Process:
    1. Validates recipient wallet exists
    2. Checks sender has sufficient balance
    3. Deducts from sender wallet
    4. Credits recipient wallet
    5. Creates transaction records for both users

    This is an ATOMIC operation - either completes fully or fails completely.

    Requires:
    - JWT authentication OR
    - API key with 'transfer' permission

    Returns:
        Transfer confirmation with new balance
    """
    user, api_key = auth_data

    # Perform the transfer (atomic operation)
    sender_wallet, recipient_wallet = WalletService.transfer_funds(
        db=db,
        sender=user,
        recipient_wallet_number=request.wallet_number,
        amount=request.amount
    )

    return TransferResponse(
        status="success",
        message="Transfer completed",
        amount=request.amount,
        recipient_wallet_number=request.wallet_number,
        sender_balance=sender_wallet.balance
    )
