from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.wallet import Wallet
from app.models.user import User
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from typing import Optional, List
from fastapi import HTTPException, status


class WalletService:
    """
    Service layer for wallet-related operations.
    Handles wallet creation, balance management, and transactions.
    """

    @staticmethod
    def create_wallet_for_user(db: Session, user: User) -> Wallet:
        """
        Create a wallet for a user with a unique wallet number.
        :param db:
        :param user: user object
        :return: Newly created wallet object
        """
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                # Generate unique wallet number
                wallet_number = Wallet.generate_wallet_number()

                # Create wallet
                wallet = Wallet(
                    user_id=user.id,
                    wallet_number=wallet_number,
                    balance=0.0
                )

                db.add(wallet)
                db.commit()
                db.refresh(wallet)

                return wallet

            except IntegrityError:
                # Wallet number collision, try again
                db.rollback()
                if attempt == max_attempts - 1:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Could not generate a unique wallet number. Please try again later."
                    )
                continue

    @staticmethod
    def get_wallet_by_user_id(db: Session, user_id: str) -> Optional[Wallet]:
        """
        Get a user's wallet by their user ID.
        :param db:
        :param user_id:
        :return: Wallet object if found, None otherwise
        """

        return db.query(Wallet).filter(Wallet.user_id == user_id).first()

    @staticmethod
    def get_wallet_by_wallet_number(db: Session, wallet_number: str) -> Optional[Wallet]:
        """
        Get wallet by wallet number.
        :param db:
        :param wallet_number:
        :return: Wallet object if found. None otherwise
        """
        return db.query(Wallet).filter(Wallet.wallet_number == wallet_number).first()

    @staticmethod
    def get_or_create_wallet(db: Session, user: User) -> Wallet:
        """
        Get existing wallet or create a new one for the user.

        :param db:
        :param user:
        :return: User's wallet
        """
        wallet = WalletService.get_wallet_by_user_id(db, user.id)

        if not wallet:
            wallet = WalletService.create_wallet_for_user(db, user)

        return wallet

    @staticmethod
    def update_balance(db: Session, wallet: Wallet, amount: float,  operation: str = "add") -> Wallet:
        """
        Update wallet balance by adding or subtracting amount.
        :param db: Database session
        :param wallet: Wallet object
        :param amount: Amount to add or subtract
        :param operation: "add" or "subtract"
        :return: Updated wallet object
        """

        if operation == "add":
            wallet.balance += amount
        elif operation == "subtract":
            if wallet.balance < amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient balance in wallet."
                )
            wallet.balance -= amount
        else:
            raise ValueError(f"Invalid operation: {operation}. Use 'add' or 'subtract'.")

        db.commit()
        db.refresh()

        return wallet

    @staticmethod
    def create_transaction(
            db: Session,
            user_id: str,
            wallet_id: str,
            transaction_type: TransactionType,
            amount: float,
            status: TransactionStatus = TransactionStatus.PENDING,
            reference: Optional[str] = None,
            recipient_wallet_number: Optional[str] = None,
            description: Optional[str] = None
    ) -> Transaction:
        """
        Create a transaction record
        :param db: Database session
        :param user_id: User's ID
        :param wallet_id: Wallet's ID
        :param transaction_type: Type of transaction
        :param amount: Transaction amount
        :param status:
        :param reference:
        :param recipient_wallet_number:
        :param description:
        :return: Created Transaction object
        """
        transaction = Transaction(
            user_id=user_id,
            wallet_id=wallet_id,
            type=transaction_type,
            amount=amount,
            status=status,
            reference=reference,
            recipient_wallet_number=recipient_wallet_number,
            description=description
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return transaction

    @staticmethod
    def get_transaction_by_reference(db: Session, reference: str) -> Optional[Transaction]:
        """
        Get a transaction by its reference.
        :param db: Database session
        :param reference: Transaction reference
        :return: Transaction object if found, None otherwise
        """
        return db.query(Transaction).filter(Transaction.reference == reference).first()

    @staticmethod
    def get_user_transaction(
            db: Session,
            user_id: str,
            limit: int = 50,
            offset: int = 0
    ):
        """
        Get paginated transaction history for a user.
        :param db:
        :param user_id:
        :param limit: Maximum number of records to return
        :param offset: Number of transactions to skip
        :return: List of transactions
        """
        return db.query(Transaction).filter(Transaction.user_id == user_id)\
        .order_by(Transaction.created_at.desc())\
        .limit(limit).offset(offset).all()
