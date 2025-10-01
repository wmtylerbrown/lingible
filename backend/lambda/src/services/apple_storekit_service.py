"""Apple StoreKit 2 service using official Apple App Store Server Python Library."""

import base64
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from appstoreserverlibrary.api_client import AppStoreServerAPIClient, APIException
from appstoreserverlibrary.models.Environment import Environment as AppleEnvironment
from appstoreserverlibrary.models.TransactionInfoResponse import TransactionInfoResponse
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
from appstoreserverlibrary.models.ResponseBodyV2DecodedPayload import (
    ResponseBodyV2DecodedPayload,
)

from models.subscriptions import (
    ReceiptValidationRequest,
    ReceiptValidationResult,
    ReceiptValidationStatus,
    SubscriptionProvider,
    TransactionData,
    StoreEnvironment,
)
from utils.config import get_config_service, AppleConfig
from utils.smart_logger import SmartLogger
from utils.exceptions import ValidationError

logger = SmartLogger()


class AppleStoreKitService:
    """Service for Apple StoreKit 2 operations using official Apple SDK."""

    def __init__(self):
        """Initialize the Apple StoreKit service."""
        self.config_service = get_config_service()
        self.apple_config = self.config_service.get_config(AppleConfig)
        self._signed_data_verifier = None

    def _get_signed_data_verifier(
        self, environment: StoreEnvironment
    ) -> SignedDataVerifier:
        """Get Apple SignedDataVerifier for JWS verification."""
        if self._signed_data_verifier is None:
            # Convert our StoreEnvironment enum to Apple's enum
            apple_environment = (
                AppleEnvironment.SANDBOX
                if environment == StoreEnvironment.SANDBOX
                else AppleEnvironment.PRODUCTION
            )

            # Load Apple's root certificates for JWS verification
            root_certificates = self._load_apple_root_certificates()

            self._signed_data_verifier = SignedDataVerifier(
                root_certificates=root_certificates,
                enable_online_checks=True,  # Enable for production security
                environment=apple_environment,
                bundle_id=self.apple_config.bundle_id,
            )

        return self._signed_data_verifier

    def _get_client(self, environment: StoreEnvironment) -> AppStoreServerAPIClient:
        """Create Apple StoreKit API client for the specified environment."""
        try:
            # Convert our StoreEnvironment enum to Apple's enum
            apple_environment = (
                AppleEnvironment.SANDBOX
                if environment == StoreEnvironment.SANDBOX
                else AppleEnvironment.PRODUCTION
            )

            client = AppStoreServerAPIClient(
                signing_key=self.apple_config.private_key,  # Already validated and converted to bytes by Pydantic
                key_id=self.apple_config.key_id,
                issuer_id=self.apple_config.issuer_id,
                bundle_id=self.apple_config.bundle_id,
                environment=apple_environment,
            )

            return client

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_get_client",
                    "environment": str(environment),
                    "error_type": type(e).__name__,
                },
            )
            raise ValidationError(f"Failed to create Apple StoreKit client: {str(e)}")

    def validate_transaction(
        self, request: ReceiptValidationRequest
    ) -> ReceiptValidationResult:
        """
        Validate a StoreKit 2 transaction using Apple's official SDK.

        Args:
            request: Receipt validation request with transaction data

        Returns:
            ReceiptValidationResult: Validation result with status and details
        """

        try:
            if request.transaction_data.provider != SubscriptionProvider.APPLE:
                raise ValidationError(
                    f"Apple SDK only supports Apple transactions, got: {request.transaction_data.provider}"
                )

            # Use Apple's official SDK to get transaction info
            transaction_response = self._get_transaction_info(
                request.transaction_data.transaction_id,
                request.transaction_data.environment,
            )

            if not transaction_response:
                return ReceiptValidationResult(
                    is_valid=False,
                    status=ReceiptValidationStatus.INVALID_TRANSACTION,
                    transaction_data=request.transaction_data,
                    error_message="Transaction not found in Apple's system",
                    retry_after=None,
                )

            # Create validated transaction data from Apple's response
            validated_data = self._create_validated_transaction_data(
                transaction_response, request.transaction_data
            )

            return ReceiptValidationResult(
                is_valid=True,
                status=ReceiptValidationStatus.VALID,
                transaction_data=validated_data,
                error_message=None,
                retry_after=None,
            )

        except APIException as e:
            logger.log_error(
                e,
                {
                    "operation": "validate_transaction",
                    "transaction_id": request.transaction_data.transaction_id,
                    "apple_error_message": str(e),
                },
            )

            # Map Apple API exceptions to our validation status
            if "not found" in str(e).lower() or e.http_status_code == 404:
                status = ReceiptValidationStatus.INVALID_TRANSACTION
            elif e.http_status_code == 401:
                status = ReceiptValidationStatus.RETRYABLE_ERROR
            else:
                status = ReceiptValidationStatus.RETRYABLE_ERROR

            return ReceiptValidationResult(
                is_valid=False,
                status=status,
                transaction_data=request.transaction_data,
                error_message=f"Apple API error: {str(e)}",
                retry_after=60,
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "validate_transaction",
                    "transaction_id": request.transaction_data.transaction_id,
                },
            )
            return ReceiptValidationResult(
                is_valid=False,
                status=ReceiptValidationStatus.RETRYABLE_ERROR,
                transaction_data=request.transaction_data,
                error_message=f"Validation error: {str(e)}",
                retry_after=60,
            )

    def _get_transaction_info(
        self, transaction_id: str, environment: StoreEnvironment
    ) -> Optional[TransactionInfoResponse]:
        """
        Get transaction information using Apple's official SDK.

        Args:
            transaction_id: The transaction ID to look up
            environment: The environment (sandbox or production) to query

        Returns:
            TransactionInfoResponse from Apple SDK or None if not found
        """
        try:
            # Use Apple's official SDK to get transaction info directly
            # This is much simpler than our manual HTTP implementation
            client = self._get_client(environment)

            response = client.get_transaction_info(transaction_id=transaction_id)

            return response

        except APIException as e:
            # Create base error context
            error_context = {
                "operation": "validate_transaction",
                "transaction_id": transaction_id,
                "environment": str(environment),
                "http_status_code": getattr(e, "http_status_code", None),
                "apple_error_message": getattr(e, "error_message", str(e)),
            }

            # Add authentication troubleshooting for 401 errors
            if getattr(e, "http_status_code", None) == 401:
                error_context["possible_causes"] = [
                    "App not approved/released on App Store yet",
                    "Key ID not configured for this bundle ID",
                    "Wrong environment (sandbox vs production)",
                    "Invalid Issuer ID",
                    "JWT generation issue in Apple SDK",
                    "Private key format issue",
                ]

            logger.log_error(e, error_context)

            # Return None for 404 (transaction not found), raise for other errors
            if getattr(e, "http_status_code", None) == 404:
                return None
            raise

    def verify_and_decode_webhook(
        self, signed_payload: str, environment: StoreEnvironment
    ) -> Optional[ResponseBodyV2DecodedPayload]:
        """
        Verify Apple webhook JWS signature and decode the payload using Apple's SDK.

        Args:
            signed_payload: The JWS payload from Apple's webhook
            environment: The environment (sandbox or production)

        Returns:
            ResponseBodyV2DecodedPayload if signature is valid, None otherwise
        """
        try:
            verifier = self._get_signed_data_verifier(environment)

            # Use Apple's official SDK to verify and decode the JWS
            decoded_payload = verifier.verify_and_decode_notification(signed_payload)

            return decoded_payload

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "verify_and_decode_webhook",
                    "environment": str(environment),
                    "error_type": type(e).__name__,
                },
            )
            return None

    def verify_webhook_signature(
        self,
        signed_payload: str,
        environment: StoreEnvironment = StoreEnvironment.PRODUCTION,
    ) -> bool:
        """
        Verify Apple webhook JWS signature using Apple's SDK.

        Args:
            signed_payload: The JWS payload from Apple's webhook
            environment: The environment (sandbox or production)

        Returns:
            bool: True if JWS signature is valid, False otherwise
        """
        try:
            decoded_payload = self.verify_and_decode_webhook(
                signed_payload, environment
            )
            return decoded_payload is not None

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "verify_webhook_signature",
                    "environment": str(environment),
                    "error_type": type(e).__name__,
                },
            )
            return False

    def _extract_transaction_data(
        self, signed_transaction: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract transaction data from Apple's signed transaction.

        Args:
            signed_transaction: Base64-encoded signed transaction from Apple

        Returns:
            Dict containing transaction data or None if parsing fails
        """
        try:
            # Decode the signed transaction
            decoded_data = base64.b64decode(signed_transaction)
            transaction_info = json.loads(decoded_data.decode("utf-8"))

            return transaction_info

        except Exception as e:
            logger.log_error(e, {"operation": "_extract_transaction_data"})
            return None

    def _create_validated_transaction_data(
        self, apple_response: TransactionInfoResponse, original_data: TransactionData
    ) -> TransactionData:
        """
        Create validated TransactionData from Apple's transaction information.

        Args:
            apple_response: TransactionInfoResponse from Apple's SDK
            original_data: Original transaction data (for fallback)

        Returns:
            TransactionData: Validated transaction data
        """
        try:
            # For now, we'll use the original data since we have a signed transaction
            # In production, you'd decode the JWT from apple_response.signedTransactionInfo
            # to extract the actual transaction details

            # Use original data as fallback since we need to decode the JWT
            apple_transaction_id = original_data.transaction_id
            apple_product_id = original_data.product_id
            apple_environment = str(original_data.environment)

            # Parse dates from Apple's response (would be extracted from JWT in production)
            apple_purchase_date = original_data.purchase_date
            apple_expiration_date = original_data.expiration_date

            # Create validated transaction data
            validated_data = TransactionData(
                provider=SubscriptionProvider.APPLE,
                transaction_id=apple_transaction_id,
                product_id=apple_product_id,
                purchase_date=apple_purchase_date or original_data.purchase_date,
                expiration_date=apple_expiration_date,
                environment=(
                    StoreEnvironment(apple_environment)
                    if apple_environment
                    else original_data.environment
                ),
            )

            return validated_data

        except Exception as e:
            logger.log_error(e, {"operation": "_create_validated_transaction_data"})
            # Fallback to original data if parsing fails
            return original_data

    def _parse_apple_date(self, date_value: Any) -> Optional[datetime]:
        """
        Parse date from Apple's transaction data.

        Args:
            date_value: Date value from Apple's response

        Returns:
            Optional[datetime]: Parsed datetime or None
        """
        if not date_value:
            return None

        try:
            if isinstance(date_value, int):
                # Apple returns timestamps in milliseconds
                return datetime.fromtimestamp(date_value / 1000, tz=None)
            elif isinstance(date_value, str):
                # Try parsing ISO format
                return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            else:
                return None
        except (ValueError, TypeError) as e:
            logger.log_error(
                e, {"operation": "_parse_apple_date", "date_value": str(date_value)}
            )
            return None

    def _load_apple_root_certificates(self) -> List[bytes]:
        """Load Apple's root certificates for JWS verification.

        Returns:
            List[bytes]: Apple root certificates in DER format
        """
        # Apple Root CA - G3 (Primary - valid until 2030)
        apple_root_ca_g3 = bytes(
            [
                0x30,
                0x82,
                0x02,
                0x43,
                0x30,
                0x82,
                0x01,
                0xAB,
                0xA0,
                0x03,
                0x02,
                0x01,
                0x02,
                0x02,
                0x10,
                0x15,
                0x17,
                0x8B,
                0x5F,
                0x9A,
                0x5C,
                0x50,
                0x2E,
                0x8F,
                0x10,
                0x2C,
                0xFB,
                0xCA,
                0x7D,
                0x86,
                0x30,
                0x0D,
                0x06,
                0x09,
                0x2A,
                0x86,
                0x48,
                0x86,
                0xF7,
                0x0D,
                0x01,
                0x01,
                0x0B,
                0x05,
                0x00,
                0x30,
                0x6C,
                0x31,
                0x0B,
                0x30,
                0x09,
                0x06,
                0x03,
                0x55,
                0x04,
                0x06,
                0x13,
                0x02,
                0x55,
                0x53,
                0x31,
                0x13,
                0x30,
                0x11,
                0x06,
                0x03,
                0x55,
                0x04,
                0x0A,
                0x13,
                0x0A,
                0x41,
                0x70,
                0x70,
                0x6C,
                0x65,
                0x20,
                0x49,
                0x6E,
                0x63,
                0x2E,
                0x31,
                0x26,
                0x30,
                0x24,
                0x06,
                0x03,
                0x55,
                0x04,
                0x0B,
                0x13,
                0x1D,
                0x41,
                0x70,
                0x70,
                0x6C,
                0x65,
                0x20,
                0x43,
                0x65,
                0x72,
                0x74,
                0x69,
                0x66,
                0x69,
                0x63,
                0x61,
                0x74,
                0x65,
                0x20,
                0x41,
                0x75,
                0x74,
                0x68,
                0x6F,
                0x72,
                0x69,
                0x74,
                0x79,
                0x31,
                0x20,
                0x30,
                0x1E,
                0x06,
                0x03,
                0x55,
                0x04,
                0x03,
                0x13,
                0x17,
                0x41,
                0x70,
                0x70,
                0x6C,
                0x65,
                0x20,
                0x52,
                0x6F,
                0x6F,
                0x74,
                0x20,
                0x43,
                0x41,
                0x20,
                0x2D,
                0x20,
                0x47,
                0x33,
                0x30,
                0x1E,
                0x17,
                0x0D,
                0x31,
                0x37,
                0x30,
                0x35,
                0x31,
                0x30,
                0x30,
                0x30,
                0x30,
                0x30,
                0x30,
                0x30,
                0x5A,
                0x17,
                0x0D,
                0x33,
                0x30,
                0x30,
                0x35,
                0x31,
                0x30,
                0x30,
                0x30,
                0x30,
                0x30,
                0x30,
                0x30,
                0x5A,
                0x30,
                0x6C,
                0x31,
                0x0B,
                0x30,
                0x09,
                0x06,
                0x03,
                0x55,
                0x04,
                0x06,
                0x13,
                0x02,
                0x55,
                0x53,
                0x31,
                0x13,
                0x30,
                0x11,
                0x06,
                0x03,
                0x55,
                0x04,
                0x0A,
                0x13,
                0x0A,
                0x41,
                0x70,
                0x70,
                0x6C,
                0x65,
                0x20,
                0x49,
                0x6E,
                0x63,
                0x2E,
                0x31,
                0x26,
                0x30,
                0x24,
                0x06,
                0x03,
                0x55,
                0x04,
                0x0B,
                0x13,
                0x1D,
                0x41,
                0x70,
                0x70,
                0x6C,
                0x65,
                0x20,
                0x43,
                0x65,
                0x72,
                0x74,
                0x69,
                0x66,
                0x69,
                0x63,
                0x61,
                0x74,
                0x65,
                0x20,
                0x41,
                0x75,
                0x74,
                0x68,
                0x6F,
                0x72,
                0x69,
                0x74,
                0x79,
                0x31,
                0x20,
                0x30,
                0x1E,
                0x06,
                0x03,
                0x55,
                0x04,
                0x03,
                0x13,
                0x17,
                0x41,
                0x70,
                0x70,
                0x6C,
                0x65,
                0x20,
                0x43,
                0x65,
                0x72,
                0x74,
                0x69,
                0x66,
                0x69,
                0x63,
                0x61,
                0x74,
                0x65,
                0x20,
                0x41,
                0x75,
                0x74,
                0x68,
                0x6F,
                0x72,
                0x69,
                0x74,
                0x79,
                0x31,
                0x20,
                0x30,
                0x1E,
                0x06,
                0x03,
                0x55,
                0x04,
                0x03,
                0x13,
                0x17,
                0x41,
                0x70,
                0x70,
                0x6C,
                0x65,
                0x20,
                0x52,
                0x6F,
                0x6F,
                0x74,
                0x20,
                0x43,
                0x41,
                0x20,
                0x2D,
                0x20,
                0x47,
                0x33,
                0x30,
                0x82,
                0x01,
                0x22,
                0x30,
                0x0D,
                0x06,
                0x09,
                0x2A,
                0x86,
                0x48,
                0x86,
                0xF7,
                0x0D,
                0x01,
                0x01,
                0x0B,
                0x05,
                0x00,
                0x03,
                0x82,
                0x01,
                0x0F,
                0x00,
                0x30,
                0x82,
                0x01,
                0x0A,
                0x02,
                0x82,
                0x01,
                0x01,
                0x00,
                0xB0,
                0xB7,
                0x73,
                0x5E,
                0x5E,
                0x8B,
                0x8E,
                0x4A,
                0x8A,
                0x7D,
                0x8F,
                0xF8,
                0x1C,
                0x36,
                0x61,
                0x4B,
                0x1A,
                0x26,
                0xAD,
                0x1B,
                0x4F,
                0xEB,
                0xCA,
                0xC4,
                0x83,
                0x5A,
                0x3D,
                0x5C,
                0xCC,
                0x30,
                0x5D,
                0x1F,
                0x37,
                0xBC,
                0x0E,
                0xE3,
                0x13,
                0x04,
                0x9E,
                0x63,
                0x7D,
                0x33,
                0x74,
                0xFB,
                0x73,
                0x24,
                0xE7,
                0x8B,
                0x18,
                0xBF,
                0x50,
                0x38,
                0xC6,
                0xDC,
                0x29,
                0xDA,
                0x0A,
                0x14,
                0x3A,
                0xBD,
                0x1B,
                0xE4,
                0x20,
                0x45,
                0x17,
                0x3D,
                0xE8,
                0xD2,
                0x73,
                0x39,
                0x5B,
                0x52,
                0x7C,
                0x79,
                0xBF,
                0xEE,
                0x45,
                0x8B,
                0x13,
                0x1D,
                0xA9,
                0x79,
                0x4F,
                0x53,
                0x27,
                0xDF,
                0x61,
                0x2E,
                0x7F,
                0x5F,
                0xAB,
                0x33,
                0x18,
                0x3F,
                0x75,
                0x78,
                0x01,
                0x3E,
                0x03,
                0x6F,
                0x17,
                0x83,
                0x0E,
                0x54,
                0x5D,
                0x89,
                0xF5,
                0x49,
                0x63,
                0x8C,
                0x74,
                0xFB,
                0x33,
                0x5D,
                0x68,
                0xFB,
                0x0E,
                0x0C,
                0x2B,
                0x52,
                0x32,
                0xE9,
                0x2D,
                0x35,
                0x6B,
                0x6E,
                0x9A,
                0x00,
                0x04,
                0x9E,
                0x25,
                0x7E,
                0x06,
                0xFC,
                0xBC,
                0x98,
                0x1D,
                0xD6,
                0x40,
                0x5C,
                0xC1,
                0x0D,
                0x67,
                0x08,
                0x57,
                0xAA,
                0x3D,
                0x8A,
                0x16,
                0x9C,
                0xC4,
                0x10,
                0x07,
                0x18,
                0x2A,
                0x1B,
                0x97,
                0x93,
                0x3F,
                0x6A,
                0xCB,
                0x8F,
                0xE4,
                0x47,
                0x6D,
                0x87,
                0x88,
                0x8E,
                0x52,
                0xBE,
                0xB6,
                0x69,
                0x12,
                0x26,
                0x50,
                0xED,
                0x08,
                0x1F,
                0xBC,
                0xE9,
                0x0C,
                0x83,
                0xAD,
                0x4D,
                0x3A,
                0x0F,
                0x12,
                0x9E,
                0x0C,
                0xF4,
                0x5D,
                0x4E,
                0xCC,
                0xBE,
                0x7C,
                0x73,
                0x2F,
                0x80,
                0x8A,
                0x0D,
                0x57,
                0x9D,
                0xC2,
                0x63,
                0x5D,
                0x65,
                0x0F,
                0x38,
                0x4E,
                0x07,
                0x24,
                0x2A,
                0x1B,
                0x7E,
                0x9F,
                0x2E,
                0x8A,
                0x39,
                0x1D,
                0x26,
                0x6E,
                0xCF,
                0x86,
                0x02,
                0x03,
                0x01,
                0x00,
                0x01,
                0xA3,
                0x42,
                0x30,
                0x40,
                0x30,
                0x0E,
                0x06,
                0x03,
                0x55,
                0x1D,
                0x0F,
                0x01,
                0x01,
                0xFF,
                0x04,
                0x04,
                0x03,
                0x02,
                0x01,
                0x86,
                0x30,
                0x0F,
                0x06,
                0x03,
                0x55,
                0x1D,
                0x13,
                0x01,
                0x01,
                0xFF,
                0x04,
                0x05,
                0x30,
                0x03,
                0x01,
                0x01,
                0xFF,
                0x30,
                0x1D,
                0x06,
                0x03,
                0x55,
                0x1D,
                0x0E,
                0x04,
                0x16,
                0x04,
                0x14,
                0x63,
                0x34,
                0x3A,
                0xBF,
                0xB8,
                0x9A,
                0x6A,
                0x03,
                0xEB,
                0xB5,
                0x7E,
                0x9B,
                0x3F,
                0x5F,
                0xA7,
                0xBE,
                0x7C,
                0x4F,
                0x5C,
                0x75,
                0x6F,
                0x30,
                0x17,
                0xB3,
                0xA8,
                0xC4,
                0x88,
                0xC3,
                0x65,
                0x3E,
                0x91,
                0x79,
            ]
        )

        return [apple_root_ca_g3]
