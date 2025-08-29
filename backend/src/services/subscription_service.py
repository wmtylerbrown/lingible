"""Subscription service for GenZ slang translation app."""

from typing import Optional, List
from datetime import datetime, timezone
import uuid

from ..models.subscriptions import (
    Subscription,
    SubscriptionHistory,
    SubscriptionProvider,
    SubscriptionStatus,
    SubscriptionAction,
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
)
from ..models.users import UserTier
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.user_repository import UserRepository
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
        self.subscription_repository = SubscriptionRepository()
        self.user_repository = UserRepository()

    @tracer.trace_method("create_subscription")
    def create_subscription(
        self, user_id: str, request: CreateSubscriptionRequest
    ) -> Subscription:
        """Create a new subscription for a user."""
        logger.log_business_event("subscription_created", {
            "user_id": user_id,
            "provider": request.provider.value,
            "tier": request.tier
        })

        try:
            # Validate user exists
            user = self.user_repository.get_user(user_id)
            if not user:
                raise ValidationError("User not found", error_code="USER_NOT_FOUND")

            # Validate tier
            try:
                tier = UserTier(request.tier)
            except ValueError:
                raise ValidationError(
                    f"Invalid tier: {request.tier}",
                    error_code="INVALID_TIER"
                )

            # Check if user already has an active subscription
            existing_subscription = self.subscription_repository.get_active_subscription(user_id)
            if existing_subscription:
                raise BusinessLogicError(
                    "User already has an active subscription",
                    error_code="ACTIVE_SUBSCRIPTION_EXISTS"
                )

            # Create subscription
            subscription = Subscription(
                subscription_id=str(uuid.uuid4()),
                user_id=user_id,
                provider=request.provider,
                tier=request.tier,
                status=SubscriptionStatus.ACTIVE,
                provider_data=request.provider_data,
                start_date=datetime.now(timezone.utc),
                end_date=self._calculate_end_date(request.provider_data, request.provider),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Create subscription history entry
            history = SubscriptionHistory(
                history_id=str(uuid.uuid4()),
                user_id=user_id,
                subscription_id=subscription.subscription_id,
                action=SubscriptionAction.UPGRADE,
                old_tier=user.tier.value,
                new_tier=request.tier,
                provider=request.provider,
                provider_data=request.provider_data,
                created_at=datetime.now(timezone.utc),
            )

            # Update user tier
            user.tier = tier
            user.updated_at = datetime.now(timezone.utc)

            # Save all changes atomically
            self.subscription_repository.save_subscription_with_history(
                subscription, history, user
            )

            logger.log_business_event("subscription_created_success", {
                "user_id": user_id,
                "subscription_id": subscription.subscription_id,
                "tier": request.tier
            })

            return subscription

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.log_error(e, {"operation": "create_subscription", "user_id": user_id})
            raise SystemError("Failed to create subscription", error_code="SUBSCRIPTION_CREATE_FAILED")

    @tracer.trace_method("update_subscription")
    def update_subscription(
        self, user_id: str, subscription_id: str, request: UpdateSubscriptionRequest
    ) -> Subscription:
        """Update an existing subscription."""
        logger.log_business_event("subscription_updated", {
            "user_id": user_id,
            "subscription_id": subscription_id
        })

        try:
            # Get existing subscription
            subscription = self.subscription_repository.get_subscription(subscription_id)
            if not subscription:
                raise ValidationError("Subscription not found", error_code="SUBSCRIPTION_NOT_FOUND")

            # Verify ownership
            if subscription.user_id != user_id:
                raise ValidationError("Subscription not found", error_code="SUBSCRIPTION_NOT_FOUND")

            # Track changes for history
            old_status = subscription.status
            old_tier = subscription.tier
            old_end_date = subscription.end_date

            # Update fields
            if request.status is not None:
                subscription.status = request.status

            if request.provider_data is not None:
                subscription.provider_data.update(request.provider_data)

            if request.end_date is not None:
                subscription.end_date = request.end_date

            subscription.updated_at = datetime.now(timezone.utc)

            # Determine action for history
            action = self._determine_action(old_status, subscription.status, old_tier, subscription.tier)

            # Create history entry if there are meaningful changes
            history = None
            if action != SubscriptionAction.RENEWAL or old_end_date != subscription.end_date:
                history = SubscriptionHistory(
                    history_id=str(uuid.uuid4()),
                    user_id=user_id,
                    subscription_id=subscription_id,
                    action=action,
                    old_tier=old_tier,
                    new_tier=subscription.tier,
                    provider=subscription.provider,
                    provider_data=subscription.provider_data,
                    created_at=datetime.now(timezone.utc),
                )

            # Update user tier if subscription tier changed
            user = None
            if old_tier != subscription.tier:
                user = self.user_repository.get_user(user_id)
                if user:
                    try:
                        user.tier = UserTier(subscription.tier)
                        user.updated_at = datetime.now(timezone.utc)
                    except ValueError:
                        logger.log_error(ValueError(f"Invalid tier: {subscription.tier}"), {
                            "operation": "update_subscription",
                            "subscription_id": subscription_id,
                            "tier": subscription.tier
                        })

            # Save changes
            self.subscription_repository.update_subscription_with_history(
                subscription, history, user
            )

            logger.log_business_event("subscription_updated_success", {
                "user_id": user_id,
                "subscription_id": subscription_id,
                "action": action.value
            })

            return subscription

        except ValidationError:
            raise
        except Exception as e:
            logger.log_error(e, {"operation": "update_subscription", "user_id": user_id, "subscription_id": subscription_id})
            raise SystemError("Failed to update subscription", error_code="SUBSCRIPTION_UPDATE_FAILED")

    @tracer.trace_method("get_user_subscriptions")
    def get_user_subscriptions(self, user_id: str) -> List[Subscription]:
        """Get all subscriptions for a user."""
        logger.log_business_event("get_user_subscriptions", {"user_id": user_id})

        try:
            subscriptions = self.subscription_repository.get_user_subscriptions(user_id)
            return subscriptions

        except Exception as e:
            logger.log_error(e, {"operation": "get_user_subscriptions", "user_id": user_id})
            raise SystemError("Failed to get subscriptions", error_code="SUBSCRIPTION_GET_FAILED")

    @tracer.trace_method("get_active_subscription")
    def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get the active subscription for a user."""
        logger.log_business_event("get_active_subscription", {"user_id": user_id})

        try:
            subscription = self.subscription_repository.get_active_subscription(user_id)
            return subscription

        except Exception as e:
            logger.log_error(e, {"operation": "get_active_subscription", "user_id": user_id})
            raise SystemError("Failed to get active subscription", error_code="SUBSCRIPTION_GET_FAILED")

    @tracer.trace_method("get_subscription_history")
    def get_subscription_history(self, user_id: str, limit: int = 10) -> List[SubscriptionHistory]:
        """Get subscription history for a user."""
        logger.log_business_event("get_subscription_history", {
            "user_id": user_id,
            "limit": limit
        })

        try:
            history = self.subscription_repository.get_subscription_history(user_id, limit)
            return history

        except Exception as e:
            logger.log_error(e, {"operation": "get_subscription_history", "user_id": user_id})
            raise SystemError("Failed to get subscription history", error_code="SUBSCRIPTION_HISTORY_FAILED")

    @tracer.trace_method("cancel_subscription")
    def cancel_subscription(self, user_id: str, subscription_id: str) -> Subscription:
        """Cancel a subscription."""
        logger.log_business_event("cancel_subscription", {
            "user_id": user_id,
            "subscription_id": subscription_id
        })

        try:
            # Get subscription
            subscription = self.subscription_repository.get_subscription(subscription_id)
            if not subscription:
                raise ValidationError("Subscription not found", error_code="SUBSCRIPTION_NOT_FOUND")

            # Verify ownership
            if subscription.user_id != user_id:
                raise ValidationError("Subscription not found", error_code="SUBSCRIPTION_NOT_FOUND")

            # Check if already cancelled
            if subscription.status == SubscriptionStatus.CANCELLED:
                raise BusinessLogicError(
                    "Subscription is already cancelled",
                    error_code="SUBSCRIPTION_ALREADY_CANCELLED"
                )

            # Update subscription
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.updated_at = datetime.now(timezone.utc)

            # Create history entry
            history = SubscriptionHistory(
                history_id=str(uuid.uuid4()),
                user_id=user_id,
                subscription_id=subscription_id,
                action=SubscriptionAction.CANCEL,
                old_tier=subscription.tier,
                new_tier=subscription.tier,  # Same tier, just cancelled
                provider=subscription.provider,
                provider_data=subscription.provider_data,
                created_at=datetime.now(timezone.utc),
            )

            # Downgrade user to free tier
            user = self.user_repository.get_user(user_id)
            if user:
                user.tier = UserTier.FREE
                user.updated_at = datetime.now(timezone.utc)

            # Save changes
            self.subscription_repository.update_subscription_with_history(
                subscription, history, user
            )

            logger.log_business_event("subscription_cancelled_success", {
                "user_id": user_id,
                "subscription_id": subscription_id
            })

            return subscription

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.log_error(e, {"operation": "cancel_subscription", "user_id": user_id, "subscription_id": subscription_id})
            raise SystemError("Failed to cancel subscription", error_code="SUBSCRIPTION_CANCEL_FAILED")

    def _calculate_end_date(
        self, provider_data: dict, provider: SubscriptionProvider
    ) -> Optional[datetime]:
        """Calculate subscription end date from provider data."""
        try:
            if provider == SubscriptionProvider.APPLE:
                # Apple provides expires_date in receipt
                expires_date_str = provider_data.get("expires_date")
                if expires_date_str:
                    return datetime.fromisoformat(expires_date_str.replace("Z", "+00:00"))

            elif provider == SubscriptionProvider.GOOGLE:
                # Google provides expiryTimeMillis
                expiry_time_ms = provider_data.get("expiry_time")
                if expiry_time_ms:
                    return datetime.fromtimestamp(int(expiry_time_ms) / 1000, tz=timezone.utc)

            elif provider == SubscriptionProvider.STRIPE:
                # Stripe provides current_period_end
                period_end = provider_data.get("current_period_end")
                if period_end:
                    return datetime.fromtimestamp(int(period_end), tz=timezone.utc)

            # Default: no end date (ongoing subscription)
            return None

        except (ValueError, TypeError) as e:
            logger.log_error(e, {
                "operation": "parse_end_date",
                "provider": provider.value,
                "provider_data": provider_data
            })
            return None

    def _determine_action(
        self,
        old_status: SubscriptionStatus,
        new_status: SubscriptionStatus,
        old_tier: str,
        new_tier: str,
    ) -> SubscriptionAction:
        """Determine the action for history tracking."""
        if old_tier != new_tier:
            if old_tier == "free" and new_tier in ["premium", "pro"]:
                return SubscriptionAction.UPGRADE
            elif old_tier in ["premium", "pro"] and new_tier == "free":
                return SubscriptionAction.DOWNGRADE
            elif old_tier in ["premium", "pro"] and new_tier in ["premium", "pro"]:
                return SubscriptionAction.UPGRADE  # or DOWNGRADE based on tier hierarchy

        if old_status != new_status:
            if new_status == SubscriptionStatus.CANCELLED:
                return SubscriptionAction.CANCEL
            elif new_status == SubscriptionStatus.EXPIRED:
                return SubscriptionAction.FAILED_PAYMENT

        return SubscriptionAction.RENEWAL
