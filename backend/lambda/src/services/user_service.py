"""User service for user management and usage tracking."""

from datetime import datetime, timezone
from typing import Optional

from models.users import (
    User,
    UserTier,
    UserStatus,
    UserUsageResponse,
)
from models.translations import UsageLimit
from utils.logging import logger
from utils.tracing import tracer
from utils.config import get_config_service, UsageLimitsConfig
from utils.exceptions import ValidationError
from utils.timezone_utils import get_central_midnight_tomorrow, is_new_day_central_time
from repositories.user_repository import UserRepository


class UserService:
    """Service for user management and usage tracking."""

    def __init__(self) -> None:
        """Initialize user service."""
        self.config_service = get_config_service()
        self.repository = UserRepository()
        self.usage_config = self.config_service.get_config(UsageLimitsConfig)

    @tracer.trace_method("create_user")
    def create_user(
        self, user_id: str, username: str, email: str, tier: UserTier = UserTier.FREE
    ) -> User:
        """Create a new user."""
        try:
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                tier=tier,
                status=UserStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            success = self.repository.create_user(user)
            if not success:
                raise ValidationError("Failed to create user")

            logger.log_business_event(
                "user_created",
                {
                    "user_id": user_id,
                    "username": username,
                    "tier": tier,
                },
            )

            return user

        except Exception as e:
            logger.log_error(e, {"operation": "create_user", "user_id": user_id})
            raise

    @tracer.trace_method("get_user")
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            return self.repository.get_user(user_id)
        except Exception as e:
            logger.log_error(e, {"operation": "get_user", "user_id": user_id})
            return None

    @tracer.trace_method("get_user_usage")
    def get_user_usage(self, user_id: str) -> UserUsageResponse:
        """Get user usage statistics for API response (dynamic data)."""
        try:
            # Get usage limits (single DB call, tier is stored here for performance)
            usage_limits = self.repository.get_usage_limits(user_id)
            if not usage_limits:
                # Create default usage limits for new user
                # Get tier from user profile for new users
                user = self.repository.get_user(user_id)
                if not user:
                    raise ValidationError(f"User not found: {user_id}")
                usage_limits = self._create_default_usage_limits(user_id, user.tier)

            # Get limits from config based on tier (from usage limits for performance)
            if usage_limits.tier == UserTier.FREE:
                daily_limit = self.usage_config.free_daily_translations
            else:  # PREMIUM
                daily_limit = self.usage_config.premium_daily_translations

            # Check if reset date has passed and reset usage if needed (Central Time)
            if is_new_day_central_time(usage_limits.reset_daily_at):
                # Reset date has passed, reset the usage
                usage_limits.daily_used = 0
                # Update the reset date to tomorrow (Central Time midnight)
                usage_limits.reset_daily_at = get_central_midnight_tomorrow()
                # Save the reset usage limits
                self.repository.reset_daily_usage(user_id, usage_limits.tier)

            # Calculate daily remaining
            daily_remaining = max(0, daily_limit - usage_limits.daily_used)

            return UserUsageResponse(
                tier=usage_limits.tier,  # Use tier from usage limits (optimized for frequent calls)
                daily_limit=daily_limit,
                daily_used=usage_limits.daily_used,
                daily_remaining=daily_remaining,
                reset_date=usage_limits.reset_daily_at,
                current_max_text_length=self.usage_config.free_max_text_length if usage_limits.tier == UserTier.FREE else self.usage_config.premium_max_text_length,
                free_tier_max_length=self.usage_config.free_max_text_length,
                premium_tier_max_length=self.usage_config.premium_max_text_length,
                free_daily_limit=self.usage_config.free_daily_translations,
                premium_daily_limit=self.usage_config.premium_daily_translations,
            )

        except Exception as e:
            logger.log_error(e, {"operation": "get_user_usage", "user_id": user_id})
            raise

    def _create_default_usage_limits(
        self, user_id: str, tier: UserTier
    ) -> UsageLimit:
        """Create default usage limits for a user."""
        try:
            # Use Central Time midnight for reset
            tomorrow_start = get_central_midnight_tomorrow()

            usage = UsageLimit(
                tier=tier,
                daily_used=0,
                reset_daily_at=tomorrow_start,
            )

            success = self.repository.update_usage_limits(user_id, usage)
            if not success:
                raise SystemError(
                    f"Failed to create default usage limits for user {user_id}"
                )

            return usage

        except Exception as e:
            logger.log_error(
                e, {"operation": "_create_default_usage_limits", "user_id": user_id}
            )
            raise

    @tracer.trace_method("update_user")
    def update_user(self, user: User) -> bool:
        """Update user information."""
        try:
            user.updated_at = datetime.now(timezone.utc)
            success = self.repository.update_user(user)

            if not success:
                raise SystemError(f"Failed to update user {user.user_id}")

            logger.log_business_event(
                "user_updated",
                {
                    "user_id": user.user_id,
                                "tier": user.tier,
            "status": user.status,
                },
            )

            return True

        except Exception as e:
            logger.log_error(e, {"operation": "update_user", "user_id": user.user_id})
            raise

    @tracer.trace_method("increment_usage")
    def increment_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> None:
        """Atomically increment user usage (assumes limits already checked)."""
        success = self.repository.increment_usage(user_id, tier)
        if not success:
            raise SystemError(f"Failed to increment usage for user {user_id}")

    @tracer.trace_method("reset_daily_usage")
    def reset_daily_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> None:
        """Reset daily usage counter to 0."""
        success = self.repository.reset_daily_usage(user_id, tier)
        if not success:
            raise SystemError(f"Failed to reset usage for user {user_id}")

    @tracer.trace_method("upgrade_user_tier")
    def upgrade_user_tier(self, user_id: str, new_tier: UserTier) -> bool:
        """Upgrade user to a new tier."""
        try:
            user = self.repository.get_user(user_id)
            if not user:
                raise ValidationError(f"User not found: {user_id}")

            user.tier = new_tier
            user.updated_at = datetime.now(timezone.utc)

            # Update user profile
            success = self.repository.update_user(user)
            if not success:
                raise SystemError(f"Failed to update user {user_id}")

            # CRITICAL: Also update the usage limits tier to keep them in sync
            # Usage limits are the source of truth for performance (frequent get_user_usage calls)
            usage_limits = self.repository.get_usage_limits(user_id)
            if usage_limits:
                usage_limits.tier = new_tier
                success = self.repository.update_usage_limits(user_id, usage_limits)
                if not success:
                    raise SystemError(f"Failed to update usage limits tier for user {user_id}")
            else:
                # Create default usage limits with new tier
                self._create_default_usage_limits(user_id, new_tier)

            logger.log_business_event(
                "user_tier_upgraded",
                {
                    "user_id": user_id,
                    "new_tier": new_tier,
                },
            )

            return True

        except Exception as e:
            logger.log_error(e, {"operation": "upgrade_user_tier", "user_id": user_id})
            raise

    @tracer.trace_method("suspend_user")
    def suspend_user(self, user_id: str) -> bool:
        """Suspend a user account."""
        try:
            user = self.repository.get_user(user_id)
            if not user:
                raise ValidationError(f"User not found: {user_id}")

            user.status = UserStatus.SUSPENDED
            user.updated_at = datetime.now(timezone.utc)

            success = self.repository.update_user(user)

            if not success:
                raise SystemError(f"Failed to update user {user_id}")

            logger.log_business_event(
                "user_suspended",
                {
                    "user_id": user_id,
                },
            )

            return True

        except Exception as e:
            logger.log_error(e, {"operation": "suspend_user", "user_id": user_id})
            raise

    @tracer.trace_method("delete_user")
    def delete_user(self, user_id: str) -> bool:
        """Delete a user and all associated data."""
        try:
            success = self.repository.delete_user(user_id)

            if not success:
                raise SystemError(f"Failed to delete user {user_id}")

            logger.log_business_event(
                "user_deleted",
                {
                    "user_id": user_id,
                },
            )

            return True

        except Exception as e:
            logger.log_error(e, {"operation": "delete_user", "user_id": user_id})
            raise
