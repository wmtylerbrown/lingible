"""Receipt validation service for StoreKit 2 transactions."""

import json
import base64
import binascii
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests

from models.subscriptions import (
    ReceiptValidationRequest,
    ReceiptValidationResult,
    ReceiptValidationStatus,
    SubscriptionProvider,
    TransactionData,
    StoreEnvironment,
)
from utils.config import get_config_service, AppleConfig
from utils.logging import SmartLogger
from utils.exceptions import ValidationError

logger = SmartLogger()


class ReceiptValidationService:
    """Service for validating StoreKit 2 transactions."""

    def __init__(self):
        """Initialize the receipt validation service."""
        self.config_service = get_config_service()
        self.apple_config = self.config_service.get_config(AppleConfig)


    def validate_storekit2_transaction(self, request: ReceiptValidationRequest) -> ReceiptValidationResult:
        """
        Validate a StoreKit 2 transaction using Apple's Transaction API.

        This method validates StoreKit 2 transactions directly with Apple,
        which is more secure than traditional receipt validation.

        Args:
            request: Receipt validation request with StoreKit 2 transaction data

        Returns:
            ReceiptValidationResult: Validation result with status and details
        """
        logger.log_business_event(
            "storekit2_transaction_validation_started",
            {
                "provider": request.transaction_data.provider,
                "transaction_id": request.transaction_data.transaction_id,
                "user_id": request.user_id,
            },
        )

        try:
            if request.transaction_data.provider != SubscriptionProvider.APPLE:
                raise ValidationError(f"StoreKit 2 validation only supports Apple, got: {request.transaction_data.provider}")

            # For StoreKit 2, we validate the transaction directly with Apple
            # This is more secure than receipt validation
            return self._validate_apple_transaction(request)
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "validate_storekit2_transaction",
                    "transaction_id": request.transaction_data.transaction_id,
                    "provider": request.transaction_data.provider,
                },
            )
            return ReceiptValidationResult(
                is_valid=False,
                status=ReceiptValidationStatus.RETRYABLE_ERROR,
                transaction_data=request.transaction_data,
                error_message=str(e),
                retry_after=60,  # Retry after 1 minute
            )


    def _validate_apple_transaction(self, request: ReceiptValidationRequest) -> ReceiptValidationResult:
        """
        Validate Apple StoreKit 2 transaction using Apple's App Store Server API.

        This method validates StoreKit 2 transactions directly with Apple's
        App Store Server API, which is the secure way to validate transactions.

        Args:
            request: Receipt validation request with StoreKit 2 transaction data

        Returns:
            ReceiptValidationResult: Validation result with status and details
        """
        try:
            transaction_data = request.transaction_data

            # Validate that we have the required transaction data
            if not transaction_data.product_id:
                raise ValidationError("Missing product_id in StoreKit 2 transaction")

            # Validate Apple configuration before making API calls
            self._validate_apple_config()

            # Get JWT token for Apple API authentication
            jwt_token = self._get_apple_jwt_token()
            if not jwt_token:
                raise ValidationError("Failed to get Apple JWT token")

            # Validate transaction with Apple's App Store Server API
            validated_transaction = self._validate_with_apple_api(
                transaction_data.transaction_id,
                jwt_token,
                transaction_data.environment
            )

            if not validated_transaction:
                raise ValidationError("Transaction validation failed with Apple")

            # Create validated transaction data from Apple's response
            validated_transaction_data = self._create_validated_transaction_data(
                validated_transaction,
                transaction_data
            )

            logger.log_business_event(
                "storekit2_transaction_validated_with_apple",
                {
                    "transaction_id": validated_transaction_data.transaction_id,
                    "product_id": validated_transaction_data.product_id,
                    "environment": validated_transaction_data.environment,
                    "purchase_date": validated_transaction_data.purchase_date.isoformat() if validated_transaction_data.purchase_date else None,
                    "expiration_date": validated_transaction_data.expiration_date.isoformat() if validated_transaction_data.expiration_date else None,
                },
            )

            return ReceiptValidationResult(
                is_valid=True,
                status=ReceiptValidationStatus.VALID,
                transaction_data=validated_transaction_data,
                error_message=None,
                retry_after=None,
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_validate_apple_transaction",
                    "transaction_id": request.transaction_data.transaction_id,
                },
            )
            return ReceiptValidationResult(
                is_valid=False,
                status=ReceiptValidationStatus.RETRYABLE_ERROR,
                transaction_data=request.transaction_data,
                error_message=f"StoreKit 2 validation error: {str(e)}",
                retry_after=60,
            )

    def _get_apple_jwt_token(self) -> str:
        """Generate JWT token for Apple App Store Server API authentication."""
        try:
            import jwt
            from datetime import datetime, timedelta

            # JWT header
            header = {
                "alg": "ES256",
                "kid": self.apple_config.key_id,
                "typ": "JWT"
            }

            # JWT payload - using proper Apple App Store Server API format
            now = datetime.utcnow()
            payload = {
                "iss": self.apple_config.team_id,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=20)).timestamp()),  # Token expires in 20 minutes
                "aud": "appstoreconnect-v1",
                "bid": self.apple_config.bundle_id
            }

            # Ensure private key is properly formatted
            private_key = self.apple_config.private_key
            if not private_key.startswith("-----BEGIN PRIVATE KEY-----"):
                # If the private key doesn't have proper headers, add them
                private_key = f"-----BEGIN PRIVATE KEY-----\n{private_key}\n-----END PRIVATE KEY-----"

            # Generate JWT token using the private key
            token = jwt.encode(
                payload,
                private_key,
                algorithm="ES256",
                headers=header
            )

            logger.log_business_event(
                "apple_jwt_token_generated",
                {
                    "key_id": self.apple_config.key_id,
                    "team_id": self.apple_config.team_id,
                    "bundle_id": self.apple_config.bundle_id,
                    "expires_at": (now + timedelta(minutes=20)).isoformat(),
                    "token_length": len(token),
                    "private_key_has_headers": private_key.startswith("-----BEGIN PRIVATE KEY-----"),
                    "private_key_length": len(private_key),
                    "jwt_header": header,
                    "jwt_payload": payload
                }
            )

            return token

        except Exception as e:
            logger.log_error(e, {"operation": "_get_apple_jwt_token"})
            return ""

    def _validate_apple_config(self) -> None:
        """Validate Apple configuration before making API calls."""
        try:
            # Check if all required Apple configuration is present
            if not self.apple_config.private_key:
                raise ValidationError("Apple private key is missing")

            if not self.apple_config.key_id:
                raise ValidationError("Apple Key ID is missing")

            if not self.apple_config.team_id:
                raise ValidationError("Apple Team ID is missing")

            if not self.apple_config.bundle_id:
                raise ValidationError("Apple Bundle ID is missing")

            # Log configuration validation (without sensitive data)
            logger.log_business_event(
                "apple_config_validated",
                {
                    "key_id": self.apple_config.key_id,
                    "team_id": self.apple_config.team_id,
                    "bundle_id": self.apple_config.bundle_id,
                    "private_key_length": len(self.apple_config.private_key),
                    "private_key_has_headers": self.apple_config.private_key.startswith("-----BEGIN PRIVATE KEY-----")
                }
            )

        except Exception as e:
            logger.log_error(e, {"operation": "_validate_apple_config"})
            raise ValidationError(f"Apple configuration validation failed: {str(e)}")

    def _validate_with_apple_api(self, transaction_id: str, jwt_token: str, environment: StoreEnvironment) -> Optional[Dict[str, Any]]:
        """
        Validate transaction with Apple's App Store Server API.

        Args:
            transaction_id: The transaction ID to validate
            jwt_token: JWT token for authentication
            environment: Sandbox or production environment

        Returns:
            Dict containing validated transaction data from Apple
        """
        try:
            # Determine the correct API endpoint based on environment
            # Using official Apple App Store Server API endpoints from documentation
            if environment == StoreEnvironment.SANDBOX:
                api_url = "https://api.storekit-sandbox.itunes.apple.com/inApps/v1/transactions"
            else:
                api_url = "https://api.storekit.itunes.apple.com/inApps/v1/transactions"

            # Prepare headers
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json",
            }

            # Log the request details for debugging
            logger.log_business_event(
                "apple_api_request_started",
                {
                    "transaction_id": transaction_id,
                    "environment": environment,
                    "api_url": api_url,
                    "full_url": f"{api_url}/{transaction_id}",
                    "jwt_token_length": len(jwt_token),
                    "jwt_token_preview": jwt_token[:50] + "..." if len(jwt_token) > 50 else jwt_token,
                    "authorization_header": f"Bearer {jwt_token[:20]}..." if len(jwt_token) > 20 else f"Bearer {jwt_token}"
                }
            )

            # Make request to Apple's API
            # Using the correct App Store Server API endpoint format
            full_url = f"{api_url}/{transaction_id}"
            response = requests.get(
                full_url,
                headers=headers,
                timeout=30
            )

            # Log response details for debugging
            logger.log_business_event(
                "apple_api_response_received",
                {
                    "transaction_id": transaction_id,
                    "status_code": response.status_code,
                    "response_length": len(response.text) if response.text else 0
                }
            )

            if response.status_code == 200:
                response_data = response.json()
                logger.log_business_event(
                    "apple_api_validation_success",
                    {
                        "transaction_id": transaction_id,
                        "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else []
                    }
                )
                return response_data
            elif response.status_code == 404:
                logger.log_error(
                    ValueError("Transaction not found"),
                    {
                        "operation": "_validate_with_apple_api",
                        "transaction_id": transaction_id,
                        "response_text": response.text
                    }
                )
                return None
            elif response.status_code == 401:
                # Log detailed 401 error information
                logger.log_error(
                    ValueError(f"Apple API authentication failed: {response.status_code}"),
                    {
                        "operation": "_validate_with_apple_api",
                        "transaction_id": transaction_id,
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "response_headers": dict(response.headers)
                    }
                )
                return None
            else:
                logger.log_error(
                    ValueError(f"Apple API error: {response.status_code}"),
                    {
                        "operation": "_validate_with_apple_api",
                        "transaction_id": transaction_id,
                        "status_code": response.status_code,
                        "response_text": response.text
                    }
                )
                return None

        except Exception as e:
            logger.log_error(e, {"operation": "_validate_with_apple_api", "transaction_id": transaction_id})
            return None

    def _create_validated_transaction_data(self, apple_response: Dict[str, Any], original_data: TransactionData) -> TransactionData:
        """
        Create validated TransactionData from Apple's API response.

        This method extracts the actual transaction details from Apple's response,
        which is the authoritative source of truth for the transaction.

        Args:
            apple_response: Response from Apple's App Store Server API
            original_data: Original transaction data from client (for fallback)

        Returns:
            TransactionData: Validated transaction data from Apple
        """
        try:
            # Parse Apple's response structure
            # Note: This structure is based on Apple's App Store Server API documentation
            # You may need to adjust based on the actual response format

            # Extract transaction info from Apple's response
            transaction_info = apple_response.get("signedTransactionInfo", {})
            if not transaction_info:
                # If no signed transaction info, try direct fields
                transaction_info = apple_response

            # Decode the signed transaction info if it's base64 encoded
            if isinstance(transaction_info, str):
                try:
                    decoded_data = base64.b64decode(transaction_info)
                    transaction_info = json.loads(decoded_data.decode('utf-8'))
                except (binascii.Error, json.JSONDecodeError):
                    logger.log_error(
                        ValueError("Failed to decode Apple transaction info"),
                        {"operation": "_create_validated_transaction_data"}
                    )
                    return original_data

            # Extract validated data from Apple's response
            apple_transaction_id = transaction_info.get("transactionId", original_data.transaction_id)
            apple_product_id = transaction_info.get("productId", original_data.product_id)
            apple_environment = transaction_info.get("environment", original_data.environment)

            # Parse dates from Apple's response
            apple_purchase_date = self._parse_apple_date(
                transaction_info.get("purchaseDate", original_data.purchase_date.isoformat())
            )
            apple_expiration_date = self._parse_apple_date(
                transaction_info.get("expiresDate")
            )

            # Create validated transaction data using Apple's authoritative data
            validated_data = TransactionData(
                provider=SubscriptionProvider.APPLE,  # Always Apple for this validation
                transaction_id=apple_transaction_id,
                product_id=apple_product_id,
                purchase_date=apple_purchase_date or original_data.purchase_date,
                expiration_date=apple_expiration_date,
                environment=StoreEnvironment(apple_environment) if apple_environment else original_data.environment,
            )

            logger.log_business_event(
                "apple_transaction_data_extracted",
                {
                    "apple_transaction_id": apple_transaction_id,
                    "apple_product_id": apple_product_id,
                    "apple_environment": apple_environment,
                    "apple_purchase_date": apple_purchase_date.isoformat() if apple_purchase_date else None,
                    "apple_expiration_date": apple_expiration_date.isoformat() if apple_expiration_date else None,
                },
            )

            return validated_data

        except Exception as e:
            logger.log_error(e, {"operation": "_create_validated_transaction_data"})
            # Fallback to original data if parsing fails
            return original_data

    def _parse_apple_date(self, date_value: Any) -> Optional[datetime]:
        """
        Parse date from Apple's API response.

        Apple returns dates in various formats, so we need to handle them properly.

        Args:
            date_value: Date value from Apple's response (could be string, int, or None)

        Returns:
            Optional[datetime]: Parsed datetime or None
        """
        if not date_value:
            return None

        try:
            if isinstance(date_value, int):
                # Apple sometimes returns timestamps in milliseconds
                return datetime.fromtimestamp(date_value / 1000, tz=timezone.utc)
            elif isinstance(date_value, str):
                # Try parsing ISO format
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            else:
                return None
        except (ValueError, TypeError) as e:
            logger.log_error(e, {"operation": "_parse_apple_date", "date_value": str(date_value)})
            return None
