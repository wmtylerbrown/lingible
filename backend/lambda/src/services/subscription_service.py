"""Subscription service for GenZ slang translation app."""

from typing import Optional
from datetime import datetime, timezone, timedelta

from models.users import UserTier
from models.subscriptions import (
    UserSubscription,
    SubscriptionProvider,
    SubscriptionStatus,
    ReceiptValidationRequest,
    ReceiptValidationStatus,
    AppleNotificationType,
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
        self, user_id: str, provider: SubscriptionProvider, receipt_data: str, transaction_id: str
    ) -> bool:
        """Validate receipt and create subscription record (domain operation only)."""
        logger.log_business_event(
            "subscription_creation_attempt",
            {
                "user_id": user_id,
                "provider": provider,
                "transaction_id": transaction_id,
            },
        )

        try:

            # Create receipt validation request
            validation_request = ReceiptValidationRequest(
                provider=SubscriptionProvider(provider),
                receipt_data=receipt_data,
                transaction_id=transaction_id,
                user_id=user_id,
            )

            # Validate receipt with provider
            validation_result = self.receipt_validator.validate_receipt(
                validation_request
            )

            if not validation_result.is_valid:
                if validation_result.status == ReceiptValidationStatus.ALREADY_USED:
                    raise ValidationError(
                        "Receipt already used", error_code="RECEIPT_ALREADY_USED"
                    )
                elif validation_result.status == ReceiptValidationStatus.EXPIRED:
                    raise ValidationError(
                        "Receipt expired", error_code="RECEIPT_EXPIRED"
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
                        f"Invalid receipt: {validation_result.error_message}",
                        error_code="INVALID_RECEIPT",
                    )

            # Create subscription record
            subscription = UserSubscription(
                user_id=user_id,
                provider=SubscriptionProvider(provider),
                transaction_id=transaction_id,
                status=SubscriptionStatus.ACTIVE,
                start_date=datetime.now(timezone.utc),
                end_date=self._calculate_end_date(provider, receipt_data),
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
                "subscription_created_successfully",
                {
                    "user_id": user_id,
                    "transaction_id": transaction_id,
                },
            )

            return True

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.log_error(e, {"operation": "validate_and_create_subscription", "user_id": user_id})
            raise

    @tracer.trace_method("handle_apple_webhook")
    def handle_apple_webhook(
        self, notification_type: AppleNotificationType, transaction_id: str, receipt_data: str
    ) -> bool:
        """Handle Apple subscription webhook."""
        logger.log_business_event(
            "apple_webhook_received",
            {"notification_type": notification_type, "transaction_id": transaction_id},
        )

        try:
            # Find user ID by transaction ID
            user_id = self._find_user_id_by_transaction_id(transaction_id)
            if not user_id:
                logger.log_error(
                    ValueError(f"User not found for transaction: {transaction_id}"),
                    {
                        "operation": "handle_apple_webhook",
                        "transaction_id": transaction_id,
                    },
                )
                return False

            # Handle different notification types
            if notification_type == "RENEWAL":
                return self._handle_renewal(user_id, receipt_data, transaction_id)
            elif notification_type == "CANCEL":
                return self._handle_cancellation(user_id)
            elif notification_type == "FAILED_PAYMENT":
                return self._handle_failed_payment(user_id)
            else:
                logger.log_business_event(
                    "unknown_webhook_type",
                    {
                        "notification_type": notification_type,
                        "transaction_id": transaction_id,
                    },
                )
                return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "handle_apple_webhook",
                    "notification_type": notification_type,
                    "transaction_id": transaction_id,
                },
            )
            return False

    def _calculate_end_date(
        self, provider: SubscriptionProvider, receipt_data: str
    ) -> Optional[datetime]:
        """Calculate subscription end date from receipt data."""
        # TODO: Parse actual end date from receipt data
        # For now, set to 1 month from now
        return datetime.now(timezone.utc).replace(day=28) + timedelta(days=30)

    def _find_user_id_by_transaction_id(self, transaction_id: str) -> Optional[str]:
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

    def _handle_renewal(
        self, user_id: str, receipt_data: str, transaction_id: str
    ) -> bool:
        """Handle subscription renewal."""
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

        # Update subscription
        subscription.end_date = self._calculate_end_date(SubscriptionProvider.APPLE, receipt_data)
        subscription.transaction_id = transaction_id
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.updated_at = datetime.now(timezone.utc)

        success = self.subscription_repository.update_subscription(subscription)
        if success:
            logger.log_business_event(
                "subscription_renewed",
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
