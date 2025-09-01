"""Receipt validation service using official Apple and Google SDKs."""

import json
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
import requests

from models.subscriptions import (
    ReceiptValidationRequest,
    ReceiptValidationResult,
    ReceiptValidationStatus,
    SubscriptionProvider,
)
from utils.config import get_config_service, AppleConfig
from utils.logging import SmartLogger
from utils.exceptions import ValidationError

logger = SmartLogger("receipt-validation-service")


class ReceiptValidationService:
    """Service for validating receipts using official Apple and Google SDKs."""

    def __init__(self):
        """Initialize the receipt validation service."""
        self.config = AppConfig()
        self.apple_config = self.config.get_apple_store_config()
        self.google_config = self.config.get_google_play_config()

        # Initialize Google Play API client
        self._google_client = None

    @property
    def google_client(self):
        """Get Google Play API client (lazy initialization)."""
        if self._google_client is None:
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    self.google_config.get("service_account_key"),
                    scopes=["https://www.googleapis.com/auth/androidpublisher"],
                )
                self._google_client = build(
                    "androidpublisher", "v3", credentials=credentials
                )
            except Exception as e:
                logger.log_error(e, {"operation": "google_client_init"})
                self._google_client = None
        return self._google_client

    def validate_receipt(
        self, request: ReceiptValidationRequest
    ) -> ReceiptValidationResult:
        """
        Validate a receipt from Apple Store or Google Play.

        Args:
            request: Receipt validation request with provider and receipt data

        Returns:
            ReceiptValidationResult: Validation result with status and details
        """
        try:
            if request.provider == SubscriptionProvider.APPLE:
                result = self._validate_apple_receipt(request)
            elif request.provider == SubscriptionProvider.GOOGLE:
                result = self._validate_google_receipt(request)
            else:
                # This should never happen with the current enum, but handle for future extensibility
                raise ValidationError(f"Unsupported provider: {request.provider}")

            # Log validation result
            logger.log_business_event(
                "receipt_validation_completed",
                {
                    "transaction_id": request.transaction_id,
                    "provider": request.provider,
                    "is_valid": result.is_valid,
                    "status": result.status,
                    "product_id": result.product_id,
                },
            )

            return result

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "validate_receipt",
                    "transaction_id": request.transaction_id,
                    "provider": request.provider,
                },
            )
            return ReceiptValidationResult(
                is_valid=False,
                status=ReceiptValidationStatus.RETRYABLE_ERROR,
                transaction_id=request.transaction_id,
                product_id=None,
                purchase_date=None,
                expiration_date=None,
                environment=None,
                error_message=str(e),
                retry_after=60,  # Retry after 1 minute
            )

    def _validate_apple_receipt(
        self, request: ReceiptValidationRequest
    ) -> ReceiptValidationResult:
        """Validate Apple Store receipt using direct API calls."""
        try:
            shared_secret = self.apple_config.get("shared_secret")

            # Prepare request payload
            payload = {
                "receipt-data": request.receipt_data,
                "password": shared_secret,
                "exclude-old-transactions": True,
            }

            # Try production environment first
            production_url = "https://buy.itunes.apple.com/verifyReceipt"
            response = requests.post(production_url, json=payload, timeout=30)

            if response.status_code != 200:
                return ReceiptValidationResult(
                    is_valid=False,
                    status=ReceiptValidationStatus.RETRYABLE_ERROR,
                    transaction_id=request.transaction_id,
                    product_id=None,
                    purchase_date=None,
                    expiration_date=None,
                    environment=None,
                    error_message=f"Apple API request failed: {response.status_code}",
                    retry_after=60,
                )

            result_data = response.json()
            status_code = result_data.get("status", -1)

            # Check if receipt is from sandbox environment
            if status_code == 21007:
                # Retry with sandbox environment
                sandbox_url = "https://sandbox.itunes.apple.com/verifyReceipt"
                response = requests.post(sandbox_url, json=payload, timeout=30)

                if response.status_code != 200:
                    return ReceiptValidationResult(
                        is_valid=False,
                        status=ReceiptValidationStatus.RETRYABLE_ERROR,
                        transaction_id=request.transaction_id,
                        product_id=None,
                        purchase_date=None,
                        expiration_date=None,
                        environment="sandbox",
                        error_message=f"Apple sandbox API request failed: {response.status_code}",
                        retry_after=60,
                    )

                result_data = response.json()
                status_code = result_data.get("status", -1)
                environment = "sandbox"
            else:
                environment = "production"

            # Check if validation was successful
            if status_code == 0:  # Valid receipt
                # Extract transaction information
                receipt_info = result_data.get("receipt", {})
                latest_receipt_info = result_data.get("latest_receipt_info", [])

                # Get the most recent transaction
                if latest_receipt_info:
                    transaction_info = latest_receipt_info[0]
                else:
                    # Fallback to receipt info for non-renewable subscriptions
                    transaction_info = receipt_info

                # Extract transaction details
                product_id = transaction_info.get("product_id")
                purchase_date_ms = int(transaction_info.get("purchase_date_ms", 0))
                expires_date_ms = transaction_info.get("expires_date_ms")

                # Convert timestamps
                purchase_date = datetime.fromtimestamp(
                    purchase_date_ms / 1000, tz=timezone.utc
                )
                expiration_date = None
                if expires_date_ms:
                    expiration_date = datetime.fromtimestamp(
                        int(expires_date_ms) / 1000, tz=timezone.utc
                    )

                # Check if subscription is expired
                if expiration_date and expiration_date < datetime.now(timezone.utc):
                    return ReceiptValidationResult(
                        is_valid=False,
                        status=ReceiptValidationStatus.EXPIRED,
                        transaction_id=request.transaction_id,
                        product_id=product_id,
                        purchase_date=purchase_date,
                        expiration_date=expiration_date,
                        environment=environment,
                        error_message="Subscription has expired",
                        retry_after=None,
                    )

                return ReceiptValidationResult(
                    is_valid=True,
                    status=ReceiptValidationStatus.VALID,
                    transaction_id=request.transaction_id,
                    product_id=product_id,
                    purchase_date=purchase_date,
                    expiration_date=expiration_date,
                    environment=environment,
                    error_message=None,
                    retry_after=None,
                )

            else:
                # Handle different Apple status codes
                error_message = self._get_apple_error_message(status_code)
                status = self._map_apple_status_to_receipt_status(status_code)

                return ReceiptValidationResult(
                    is_valid=False,
                    status=status,
                    transaction_id=request.transaction_id,
                    product_id=None,
                    purchase_date=None,
                    expiration_date=None,
                    environment=environment,
                    error_message=error_message,
                    retry_after=(
                        300
                        if status == ReceiptValidationStatus.RETRYABLE_ERROR
                        else None
                    ),
                )

        except requests.RequestException as e:
            logger.log_error(
                e,
                {
                    "operation": "_validate_apple_receipt",
                    "transaction_id": request.transaction_id,
                },
            )
            return ReceiptValidationResult(
                is_valid=False,
                status=ReceiptValidationStatus.RETRYABLE_ERROR,
                transaction_id=request.transaction_id,
                product_id=None,
                purchase_date=None,
                expiration_date=None,
                environment=None,
                error_message=f"Apple API request error: {str(e)}",
                retry_after=60,
            )
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_validate_apple_receipt",
                    "transaction_id": request.transaction_id,
                },
            )
            return ReceiptValidationResult(
                is_valid=False,
                status=ReceiptValidationStatus.RETRYABLE_ERROR,
                transaction_id=request.transaction_id,
                product_id=None,
                purchase_date=None,
                expiration_date=None,
                environment=None,
                error_message=f"Apple validation error: {str(e)}",
                retry_after=60,
            )

    def _validate_google_receipt(
        self, request: ReceiptValidationRequest
    ) -> ReceiptValidationResult:
        """Validate Google Play receipt using Google Play Developer API."""
        try:
            if not self.google_client:
                return ReceiptValidationResult(
                    is_valid=False,
                    status=ReceiptValidationStatus.RETRYABLE_ERROR,
                    transaction_id=request.transaction_id,
                    product_id=None,
                    purchase_date=None,
                    expiration_date=None,
                    environment=None,
                    error_message="Google Play API client not initialized",
                    retry_after=60,
                )

            # Parse receipt data (Google Play sends JSON)
            try:
                receipt_data = json.loads(request.receipt_data)
            except json.JSONDecodeError:
                return ReceiptValidationResult(
                    is_valid=False,
                    status=ReceiptValidationStatus.INVALID,
                    transaction_id=request.transaction_id,
                    product_id=None,
                    purchase_date=None,
                    expiration_date=None,
                    environment=None,
                    error_message="Invalid JSON format in receipt data",
                    retry_after=None,
                )

            # Extract Google Play receipt information
            package_name = receipt_data.get("packageName")
            product_id = receipt_data.get("productId")
            purchase_token = receipt_data.get("purchaseToken")

            if not all([package_name, product_id, purchase_token]):
                return ReceiptValidationResult(
                    is_valid=False,
                    status=ReceiptValidationStatus.INVALID,
                    transaction_id=request.transaction_id,
                    product_id=None,
                    purchase_date=None,
                    expiration_date=None,
                    environment=None,
                    error_message="Missing required fields in Google Play receipt",
                    retry_after=None,
                )

            # Verify purchase with Google Play Developer API
            try:
                purchase_response = (
                    self.google_client.purchases()
                    .subscriptions()
                    .get(
                        packageName=package_name,
                        subscriptionId=product_id,
                        token=purchase_token,
                    )
                    .execute()
                )

                # Check subscription status
                payment_state = purchase_response.get("paymentState", 0)
                expiry_time_ms = purchase_response.get("expiryTimeMillis")

                # Convert expiry time
                expiration_date = None
                if expiry_time_ms:
                    expiration_date = datetime.fromtimestamp(
                        int(expiry_time_ms) / 1000, tz=timezone.utc
                    )

                # Check if subscription is expired
                if expiration_date and expiration_date < datetime.now(timezone.utc):
                    return ReceiptValidationResult(
                        is_valid=False,
                        status=ReceiptValidationStatus.EXPIRED,
                        transaction_id=request.transaction_id,
                        product_id=product_id,
                        purchase_date=None,  # Google doesn't provide purchase date in this API
                        expiration_date=expiration_date,
                        environment="production",
                        error_message="Google Play subscription has expired",
                        retry_after=None,
                    )

                # Check payment state (0 = pending, 1 = purchased, 2 = cancelled)
                if payment_state == 1:  # Purchased
                    return ReceiptValidationResult(
                        is_valid=True,
                        status=ReceiptValidationStatus.VALID,
                        transaction_id=request.transaction_id,
                        product_id=product_id,
                        purchase_date=None,
                        expiration_date=expiration_date,
                        environment="production",
                        error_message=None,
                        retry_after=None,
                    )
                elif payment_state == 2:  # Cancelled
                    return ReceiptValidationResult(
                        is_valid=False,
                        status=ReceiptValidationStatus.INVALID,
                        transaction_id=request.transaction_id,
                        product_id=product_id,
                        purchase_date=None,
                        expiration_date=expiration_date,
                        environment="production",
                        error_message="Google Play subscription is cancelled",
                        retry_after=None,
                    )
                else:  # Pending or other states
                    return ReceiptValidationResult(
                        is_valid=False,
                        status=ReceiptValidationStatus.INVALID,
                        transaction_id=request.transaction_id,
                        product_id=product_id,
                        purchase_date=None,
                        expiration_date=expiration_date,
                        environment="production",
                        error_message=f"Google Play subscription payment state: {payment_state}",
                        retry_after=None,
                    )

            except HttpError as e:
                if e.resp.status == 404:
                    return ReceiptValidationResult(
                        is_valid=False,
                        status=ReceiptValidationStatus.INVALID,
                        transaction_id=request.transaction_id,
                        product_id=product_id,
                        purchase_date=None,
                        expiration_date=None,
                        environment="production",
                        error_message="Google Play subscription not found",
                        retry_after=None,
                    )
                else:
                    return ReceiptValidationResult(
                        is_valid=False,
                        status=ReceiptValidationStatus.RETRYABLE_ERROR,
                        transaction_id=request.transaction_id,
                        product_id=product_id,
                        purchase_date=None,
                        expiration_date=None,
                        environment="production",
                        error_message=f"Google Play API error: {str(e)}",
                        retry_after=60,
                    )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_validate_google_receipt",
                    "transaction_id": request.transaction_id,
                },
            )
            return ReceiptValidationResult(
                is_valid=False,
                status=ReceiptValidationStatus.RETRYABLE_ERROR,
                transaction_id=request.transaction_id,
                product_id=None,
                purchase_date=None,
                expiration_date=None,
                environment=None,
                error_message=f"Google validation error: {str(e)}",
                retry_after=60,
            )

    def _get_apple_error_message(self, status_code: int) -> str:
        """Get human-readable error message for Apple status codes."""
        error_messages = {
            21000: "Invalid JSON",
            21002: "Invalid receipt data",
            21003: "Receipt not authenticated",
            21004: "Invalid shared secret",
            21005: "Receipt server unavailable",
            21006: "Receipt valid but subscription expired",
            21007: "Receipt is from sandbox environment",
            21008: "Receipt is from production environment",
        }
        return error_messages.get(
            status_code, f"Unknown Apple status code: {status_code}"
        )

    def _map_apple_status_to_receipt_status(
        self, status_code: int
    ) -> ReceiptValidationStatus:
        """Map Apple status codes to our receipt validation status."""
        status_mapping = {
            21000: ReceiptValidationStatus.INVALID,
            21002: ReceiptValidationStatus.INVALID,
            21003: ReceiptValidationStatus.INVALID,
            21004: ReceiptValidationStatus.INVALID,
            21005: ReceiptValidationStatus.RETRYABLE_ERROR,
            21006: ReceiptValidationStatus.EXPIRED,
            21007: ReceiptValidationStatus.ENVIRONMENT_MISMATCH,
            21008: ReceiptValidationStatus.ENVIRONMENT_MISMATCH,
        }
        return status_mapping.get(status_code, ReceiptValidationStatus.INVALID)
