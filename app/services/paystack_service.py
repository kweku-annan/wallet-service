import requests
import hmac
import hashlib
from typing import Dict, Optional, Tuple
from app.core.config import get_settings
from fastapi import HTTPException, status
import secrets

settings = get_settings()


class PaystackService:
    """
    Service for Paystack payment integration

    Handles:
    - Transaction initialization
    - Webhook signature verification
    - Transaction verification
    """

    BASE_URL = 'https://api.paystack.co'

    @staticmethod
    def generate_reference() -> str:
        """
        Generate a unique transaction reference.

        :return: Unique reference string
        """
        random_part = secrets.token_hex(4) # 8 hex chars1000000000
        return f"txn_{random_part}"

    @staticmethod
    def initialize_transaction(
            email: str,
            amount: float,
            reference: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Initialize a Paystack transaction.

        :param email: Customer's email
        :param amount: Amount in Naira (will be converted to kobo)
        :param reference: Optional custom reference
        :return: Tuple of (reference, authorization_url)
        :raises: HTTPException: If Paystack API call fails
        """
        # Generate reference if not provided
        if not reference:
            reference = PaystackService.generate_reference()

        # Convert amount to kobo (Paystack uses smallest currency unit)
        amount_kobo = int(amount * 100)

        # Prepare request
        url = f"{PaystackService.BASE_URL}/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "callback_url": settings.GOOGLE_REDIRECT_URI
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            if not data.get("status"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Paystack error: {data.get('message', 'Unknown error')}"
                )

            # Extract authorization URL
            authorization_url = data["data"]["authorization_url"]

            return reference, authorization_url

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize Paystack transaction: {str(e)}"
            )

    @staticmethod
    def verify_transaction(reference: str) -> Dict:
        """
        Verify a transaction with Paystack.

        This is used as a fallback to manually check transaction status.
        The webhook is the primary method for getting transaction updates.

        :param reference: Payment reference
        :return: Transaction data from Paystack
        :raises: HTTPException: If verification fails
        """
        url = f"{PaystackService.BASE_URL}/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            if not data.get("status"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Paystack verification error: {data.get('message', 'Unknown error')}"
                )

            return data["data"]

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify Paystack transaction: {str(e)}"
            )

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """
        Verify that a webhook request came from Paystack.

        Paystack signs all webhook requests with HMAC SHA512
        We verify the signature to ensure the request is legitimate.

        :param payload: Raw request body
        :param signature: Signature from 'x-paystack-signature' header
        :return: True if signature is valid, False otherwise
        """

        # Compute HMAC SHA512 hash
        computed_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        # Compare signatures (constant-time comparison to prevent timing attacks)
        return hmac.compare_digest(computed_signature, signature)

    @staticmethod
    def kobo_to_naira(amount_in_kob: int) -> float:
        """
        Convert amount from kobo to naira.

        :param amount_in_kob: Amount in kobo
        :return: Amount in naira
        """
        return amount_in_kob / 100.0

    @staticmethod
    def naira_to_kobo(amount_in_naira: float) -> int:
        """
        Convert amount from naira to kobo.

        :param amount_in_naira: Amount in naira
        :return: Amount in kobo
        """
        return int(amount_in_naira * 100)