"""Subscription service for GenZ slang translation app."""

from typing import Optional
from datetime import datetime, timezone, timedelta

from ..models.users import User, UserTier
from ..models.subscriptions import (
    UserSubscription,
    SubscriptionProvider,
    SubscriptionStatus,
    ReceiptValidationRequest,
    ReceiptValidationStatus,
)
from ..services.user_service import UserService
from ..services.receipt_validation_service import ReceiptValidationService
from ..repositories.subscription_repository import SubscriptionRepository
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.exceptions import (
    ValidationError,
    BusinessLogicError,
    SystemError,
)


class SubscriptionService:
    """Service for managing user subscriptions."""

    def __init__(self):
        """Initialize subscription service."""
        self.user_service = UserService()
        self.subscription_repository = SubscriptionRepository()
        self.receipt_validator = ReceiptValidationService()

    @tracer.trace_method("upgrade_user")
    def upgrade_user(
        self, user_id: str, provider: str, receipt_data: str, transaction_id: str
    ) -> User:
        """Upgrade user subscription after validating purchase."""
        logger.log_business_event(
            "user_upgrade_attempt",
            {
                "user_id": user_id,
                "provider": provider,
                "transaction_id": transaction_id,
            },
        )

        try:
            # Get user
            user = self.user_service.get_user(user_id)
            if not user:
                raise ValidationError("User not found", error_code="USER_NOT_FOUND")

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

            # Update user tier
            user.tier = UserTier.PREMIUM
            user.updated_at = datetime.now(timezone.utc)

            # Save user
            success = self.user_service.update_user(user)
            if not success:
                raise SystemError(
                    "Failed to update user", error_code="USER_UPDATE_FAILED"
                )

            # Note: Transaction deduplication is handled by the receipt validation service
            # No need to mark as used since we're not caching receipts in database

            logger.log_business_event(
                "user_upgrade_success",
                {
                    "user_id": user_id,
                    "tier": "premium",
                    "transaction_id": transaction_id,
                },
            )

            return user

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.log_error(e, {"operation": "upgrade_user", "user_id": user_id})
            raise SystemError(
                "Failed to upgrade user", error_code="USER_UPGRADE_FAILED"
            )

    @tracer.trace_method("handle_apple_webhook")
    def handle_apple_webhook(
        self, notification_type: str, transaction_id: str, receipt_data: str
    ) -> bool:
        """Handle Apple subscription webhook."""
        logger.log_business_event(
            "apple_webhook_received",
            {"notification_type": notification_type, "transaction_id": transaction_id},
        )

        try:
            # Find user by transaction ID
            user = self._find_user_by_transaction_id(transaction_id)
            if not user:
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
                return self._handle_renewal(user, receipt_data, transaction_id)
            elif notification_type == "CANCEL":
                return self._handle_cancellation(user)
            elif notification_type == "FAILED_PAYMENT":
                return self._handle_failed_payment(user)
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
        self, provider: str, receipt_data: str
    ) -> Optional[datetime]:
        """Calculate subscription end date from receipt data."""
        # TODO: Parse actual end date from receipt data
        # For now, set to 1 month from now
        return datetime.now(timezone.utc).replace(day=28) + timedelta(days=30)

    def _find_user_by_transaction_id(self, transaction_id: str) -> Optional[User]:
        """Find user by transaction ID."""
        # Find subscription by transaction ID
        subscription = self.subscription_repository.find_by_transaction_id(
            transaction_id
        )
        if not subscription:
            return None

        # Get user
        return self.user_service.get_user(subscription.user_id)

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
        self, user: User, receipt_data: str, transaction_id: str
    ) -> bool:
        """Handle subscription renewal."""
        # Get current subscription
        subscription = self.subscription_repository.get_active_subscription(
            user.user_id
        )
        if not subscription:
            logger.log_error(
                ValueError(f"No active subscription found for user: {user.user_id}"),
                {"operation": "_handle_renewal", "user_id": user.user_id},
            )
            return False

        # Update subscription
        subscription.end_date = self._calculate_end_date("apple", receipt_data)
        subscription.transaction_id = transaction_id
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.updated_at = datetime.now(timezone.utc)

        success = self.subscription_repository.update_subscription(subscription)
        if success:
            logger.log_business_event(
                "subscription_renewed",
                {"user_id": user.user_id, "transaction_id": transaction_id},
            )
        return success

    def _handle_cancellation(self, user: User) -> bool:
        """Handle subscription cancellation."""
        # Cancel subscription
        success = self.subscription_repository.cancel_subscription(user.user_id)
        if not success:
            return False

        # Update user tier
        user.tier = UserTier.FREE
        user.updated_at = datetime.now(timezone.utc)

        success = self.user_service.update_user(user)
        if success:
            logger.log_business_event(
                "subscription_cancelled", {"user_id": user.user_id}
            )
        return success

    def _handle_failed_payment(self, user: User) -> bool:
        """Handle failed payment."""
        # Get current subscription
        subscription = self.subscription_repository.get_active_subscription(
            user.user_id
        )
        if not subscription:
            logger.log_error(
                ValueError(f"No active subscription found for user: {user.user_id}"),
                {"operation": "_handle_failed_payment", "user_id": user.user_id},
            )
            return False

        # Update subscription status
        subscription.status = SubscriptionStatus.EXPIRED
        subscription.updated_at = datetime.now(timezone.utc)

        success = self.subscription_repository.update_subscription(subscription)
        if success:
            logger.log_business_event("subscription_expired", {"user_id": user.user_id})
        return success
