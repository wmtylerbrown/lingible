"""Subscription service for GenZ slang translation app."""

from typing import Optional
from datetime import datetime, timezone, timedelta

from models.subscriptions import (
    UserSubscription,
    SubscriptionProvider,
    SubscriptionStatus,
    ReceiptValidationRequest,
    ReceiptValidationStatus,
    TransactionData,
    StoreEnvironment,
)
from services.receipt_validation_service import ReceiptValidationService
from repositories.subscription_repository import SubscriptionRepository
from utils.logging import logger
from utils.tracing import tracer
from utils.exceptions import (
    ValidationError,
    BusinessLogicError,
    SystemError,
)


class SubscriptionService:
    """Service for managing user subscriptions."""

    def __init__(self):
        """Initialize subscription service."""
        self.subscription_repository = SubscriptionRepository()
        self.receipt_validator = ReceiptValidationService()

    @tracer.trace_method("validate_and_create_subscription")
    def validate_and_create_subscription(
        self, user_id: str, transaction_data: TransactionData
    ) -> bool:
        """Validate StoreKit 2 transaction and create subscription record (domain operation only)."""
        logger.log_business_event(
            "storekit2_subscription_creation_attempt",
            {
                "user_id": user_id,
                "provider": transaction_data.provider,
                "transaction_id": transaction_data.transaction_id,
                "product_id": transaction_data.product_id,
                "environment": transaction_data.environment,
            },
        )

        try:
            # StoreKit 2 validation
            validation_request = ReceiptValidationRequest(
                transaction_data=transaction_data,
                user_id=user_id,
            )

            # Validate transaction with StoreKit 2 method
            validation_result = self.receipt_validator.validate_storekit2_transaction(
                validation_request
            )

            if not validation_result.is_valid:
                if validation_result.status == ReceiptValidationStatus.ALREADY_USED:
                    raise ValidationError(
                        "Transaction already used", error_code="TRANSACTION_ALREADY_USED"
                    )
                elif validation_result.status == ReceiptValidationStatus.EXPIRED:
                    raise ValidationError(
                        "Transaction expired", error_code="TRANSACTION_EXPIRED"
                    )
                elif (
                    validation_result.status
                    == ReceiptValidationStatus.ENVIRONMENT_MISMATCH
                ):
                    raise ValidationError(
                        "Environment mismatch", error_code="ENVIRONMENT_MISMATCH"
                    )
                else:
                    raise ValidationError(
                        f"Invalid transaction: {validation_result.error_message}",
                        error_code="INVALID_TRANSACTION",
                    )

            # Create subscription record using validated data
            subscription = UserSubscription(
                user_id=user_id,
                provider=validation_result.transaction_data.provider,
                transaction_id=validation_result.transaction_data.transaction_id,
                status=SubscriptionStatus.ACTIVE,
                start_date=validation_result.transaction_data.purchase_date,
                end_date=validation_result.transaction_data.expiration_date,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Save subscription
            success = self.subscription_repository.create_subscription(subscription)
            if not success:
                raise SystemError(
                    "Failed to create subscription",
                    error_code="SUBSCRIPTION_CREATE_FAILED",
                )

            logger.log_business_event(
                "storekit2_subscription_created_successfully",
                {
                    "user_id": user_id,
                    "transaction_id": transaction_data.transaction_id,
                    "product_id": transaction_data.product_id,
                },
            )

            return True

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.log_error(e, {"operation": "validate_and_create_subscription", "user_id": user_id})
            raise


    @tracer.trace_method("handle_renewal_webhook")
    def handle_renewal_webhook(self, transaction_id: str) -> bool:
        """Handle Apple subscription renewal webhook using StoreKit 2 validation."""
        logger.log_business_event(
            "apple_renewal_webhook_received",
            {"transaction_id": transaction_id},
        )

        try:
            # Find user ID by transaction ID
            user_id = self.find_user_id_by_transaction_id(transaction_id)
            if not user_id:
                logger.log_error(
                    ValueError(f"User not found for transaction: {transaction_id}"),
                    {"operation": "handle_renewal_webhook", "transaction_id": transaction_id},
                )
                return False

            # Validate the renewal transaction with Apple's API to get real expiration date
            return self._handle_renewal_with_validation(user_id, transaction_id)

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "handle_renewal_webhook", "transaction_id": transaction_id},
            )
            return False

    @tracer.trace_method("handle_cancellation_webhook")
    def handle_cancellation_webhook(self, transaction_id: str) -> bool:
        """Handle Apple subscription cancellation webhook."""
        logger.log_business_event(
            "apple_cancellation_webhook_received",
            {"transaction_id": transaction_id},
        )

        try:
            # Find user ID by transaction ID
            user_id = self.find_user_id_by_transaction_id(transaction_id)
            if not user_id:
                logger.log_error(
                    ValueError(f"User not found for transaction: {transaction_id}"),
                    {"operation": "handle_cancellation_webhook", "transaction_id": transaction_id},
                )
                return False

            return self._handle_cancellation(user_id)

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "handle_cancellation_webhook", "transaction_id": transaction_id},
            )
            return False

    @tracer.trace_method("handle_failed_payment_webhook")
    def handle_failed_payment_webhook(self, transaction_id: str) -> bool:
        """Handle Apple subscription failed payment webhook."""
        logger.log_business_event(
            "apple_failed_payment_webhook_received",
            {"transaction_id": transaction_id},
        )

        try:
            # Find user ID by transaction ID
            user_id = self.find_user_id_by_transaction_id(transaction_id)
            if not user_id:
                logger.log_error(
                    ValueError(f"User not found for transaction: {transaction_id}"),
                    {"operation": "handle_failed_payment_webhook", "transaction_id": transaction_id},
                )
                return False

            return self._handle_failed_payment(user_id)

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "handle_failed_payment_webhook", "transaction_id": transaction_id},
            )
            return False

    def _calculate_end_date(
        self, provider: SubscriptionProvider
    ) -> Optional[datetime]:
        """Calculate subscription end date (legacy method - just extends by 30 days)."""
        # Legacy method - just extend by 30 days
        # In production, this should be replaced with Apple API validation
        return datetime.now(timezone.utc).replace(day=28) + timedelta(days=30)

    def find_user_id_by_transaction_id(self, transaction_id: str) -> Optional[str]:
        """Find user ID by transaction ID."""
        # Find subscription by transaction ID
        subscription = self.subscription_repository.find_by_transaction_id(
            transaction_id
        )
        if not subscription:
            return None

        # Return user ID only
        return subscription.user_id

    @tracer.trace_method("create_subscription")
    def create_subscription(self, user_id: str, provider: str, transaction_id: str, start_date: datetime, end_date: datetime) -> bool:
        """Create a subscription record (domain operation)."""
        try:
            subscription = UserSubscription(
                user_id=user_id,
                provider=SubscriptionProvider(provider),
                transaction_id=transaction_id,
                status=SubscriptionStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            success = self.subscription_repository.create_subscription(subscription)
            if success:
                logger.log_business_event(
                    "subscription_created",
                    {"user_id": user_id, "transaction_id": transaction_id}
                )
            return success

        except Exception as e:
            logger.log_error(e, {"operation": "create_subscription", "user_id": user_id})
            return False

    @tracer.trace_method("get_active_subscription")
    def get_active_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """Get user's active subscription."""
        try:
            return self.subscription_repository.get_active_subscription(user_id)
        except Exception as e:
            logger.log_error(
                e, {"operation": "get_active_subscription", "user_id": user_id}
            )
            return None

    @tracer.trace_method("cancel_subscription")
    def cancel_subscription(self, user_id: str) -> bool:
        """Cancel user's active subscription."""
        try:
            return self.subscription_repository.cancel_subscription(user_id)
        except Exception as e:
            logger.log_error(
                e, {"operation": "cancel_subscription", "user_id": user_id}
            )
            return False

    def _handle_renewal_with_validation(self, user_id: str, transaction_id: str) -> bool:
        """Handle subscription renewal with StoreKit 2 validation."""
        try:
            # Get current subscription
            subscription = self.subscription_repository.get_active_subscription(user_id)
            if not subscription:
                logger.log_error(
                    ValueError(f"No active subscription found for user: {user_id}"),
                    {"operation": "_handle_renewal_with_validation", "user_id": user_id},
                )
                return False

            # Create a mock TransactionData for validation (we only have transaction_id from webhook)
            # In a real implementation, you might want to fetch more details from Apple's API
            mock_transaction_data = TransactionData(
                provider=SubscriptionProvider.APPLE,
                transaction_id=transaction_id,
                product_id=subscription.transaction_id,  # Use existing product_id as fallback
                purchase_date=datetime.now(timezone.utc),  # Current time as fallback
                expiration_date=None,  # Will be determined by Apple validation
                environment=StoreEnvironment.PRODUCTION,  # Webhooks are typically production
            )

            # Validate the renewal transaction with Apple
            validation_request = ReceiptValidationRequest(
                transaction_data=mock_transaction_data,
                user_id=user_id,
            )

            validation_result = self.receipt_validator.validate_storekit2_transaction(validation_request)

            if not validation_result.is_valid:
                logger.log_error(
                    ValueError(f"Renewal transaction validation failed: {validation_result.error_message}"),
                    {"operation": "_handle_renewal_with_validation", "user_id": user_id, "transaction_id": transaction_id},
                )
                return False

            # Update subscription with validated data from Apple
            subscription.end_date = validation_result.transaction_data.expiration_date
            subscription.transaction_id = transaction_id
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.updated_at = datetime.now(timezone.utc)

            success = self.subscription_repository.update_subscription(subscription)
            if success:
                logger.log_business_event(
                    "subscription_renewed_with_validation",
                    {
                        "user_id": user_id,
                        "transaction_id": transaction_id,
                        "expiration_date": validation_result.transaction_data.expiration_date.isoformat() if validation_result.transaction_data.expiration_date else None,
                    },
                )
            return success

        except Exception as e:
            logger.log_error(e, {"operation": "_handle_renewal_with_validation", "user_id": user_id})
            return False

    def _handle_renewal(
        self, user_id: str, transaction_id: str
    ) -> bool:
        """Handle subscription renewal (legacy method - kept for backward compatibility)."""
        # Get current subscription
        subscription = self.subscription_repository.get_active_subscription(
            user_id
        )
        if not subscription:
            logger.log_error(
                ValueError(f"No active subscription found for user: {user_id}"),
                {"operation": "_handle_renewal", "user_id": user_id},
            )
            return False

        # Update subscription (legacy approach - just extend by 30 days)
        subscription.end_date = self._calculate_end_date(SubscriptionProvider.APPLE)
        subscription.transaction_id = transaction_id
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.updated_at = datetime.now(timezone.utc)

        success = self.subscription_repository.update_subscription(subscription)
        if success:
            logger.log_business_event(
                "subscription_renewed_legacy",
                {"user_id": user_id, "transaction_id": transaction_id},
            )
        return success

    def _handle_cancellation(self, user_id: str) -> bool:
        """Handle subscription cancellation from Apple webhook."""
        try:
            logger.log_business_event(
                "subscription_cancellation_received",
                {
                    "user_id": user_id,
                    "source": "apple_webhook"
                }
            )

            # Step 1: Cancel subscription in our database (archive it)
            subscription_cancelled = self.subscription_repository.cancel_subscription(user_id)
            if not subscription_cancelled:
                logger.log_error(
                    SystemError("Failed to cancel subscription in database"),
                    {"operation": "_handle_cancellation", "user_id": user_id}
                )
                return False

            # Note: User tier downgrade should be handled by UserService orchestration

            logger.log_business_event(
                "subscription_cancellation_completed",
                {
                    "user_id": user_id,
                    "subscription_archived": True
                }
            )

            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_handle_cancellation",
                    "user_id": user_id
                }
            )
            return False

    def _handle_failed_payment(self, user_id: str) -> bool:
        """Handle failed payment from Apple webhook."""
        try:
            logger.log_business_event(
                "subscription_payment_failed",
                {
                    "user_id": user_id,
                    "source": "apple_webhook"
                }
            )

            # Get current subscription
            subscription = self.subscription_repository.get_active_subscription(user_id)
            if not subscription:
                logger.log_error(
                    ValueError(f"No active subscription found for user: {user_id}"),
                    {"operation": "_handle_failed_payment", "user_id": user_id},
                )
                return False

            # Step 1: Update subscription status to EXPIRED
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.updated_at = datetime.now(timezone.utc)

            subscription_updated = self.subscription_repository.update_subscription(subscription)
            if not subscription_updated:
                logger.log_error(
                    SystemError("Failed to update subscription status"),
                    {"operation": "_handle_failed_payment", "user_id": user_id}
                )
                return False

            # Note: User tier downgrade should be handled by UserService orchestration

            logger.log_business_event(
                "subscription_payment_failure_handled",
                {
                    "user_id": user_id,
                    "subscription_status": "EXPIRED"
                }
            )

            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_handle_failed_payment",
                    "user_id": user_id
                }
            )
            return False
