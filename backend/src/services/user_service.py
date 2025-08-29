"""User service for user management and usage tracking."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..models.users import User, UserTier, UserStatus, UserUsage, UserUsageResponse
from ..models.translations import UsageLimit
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.config import get_config
from ..utils.exceptions import UsageLimitExceededError, ValidationError
from ..repositories.user_repository import UserRepository


class UserService:
    """Service for user management and usage tracking."""

    def __init__(self) -> None:
        """Initialize user service."""
        self.config = get_config()
        self.repository = UserRepository()
        self.usage_config = self.config.get_usage_limits()

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
                total_translations_used=0,
                last_translation_date=None,
                subscription_start_date=None,
                subscription_end_date=None,
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
                    "tier": tier.value,
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

    @tracer.trace_method("get_user_profile")
    def get_user_profile(self, user_id: str) -> User:
        """Get user profile for API response (static, cacheable data)."""
        try:
            user = self.repository.get_user(user_id)
            if not user:
                raise ValidationError(f"User not found: {user_id}")

            return user

        except Exception as e:
            logger.log_error(e, {"operation": "get_user_profile", "user_id": user_id})
            raise

    @tracer.trace_method("get_user_usage")
    def get_user_usage(self, user_id: str) -> UserUsageResponse:
        """Get user usage statistics for API response (dynamic data)."""
        try:
            # Get usage limits only (tier is now included)
            usage_limits = self.repository.get_usage_limits(user_id)
            if not usage_limits:
                # Create default usage limits for new user
                usage_limits = self._create_default_usage_limits_for_user(user_id)

            # Get limits from config based on tier
            tier_config = self.usage_config.get(
                usage_limits.tier, self.usage_config["free"]
            )
            daily_limit = tier_config["daily_limit"]

            # Calculate daily remaining
            daily_remaining = max(0, daily_limit - usage_limits.current_daily_usage)

            return UserUsageResponse(
                tier=usage_limits.tier,
                daily_limit=daily_limit,
                daily_used=usage_limits.current_daily_usage,
                daily_remaining=daily_remaining,
                total_used=0,  # We'll need to get this from user data if needed
                reset_date=usage_limits.reset_daily_at or datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.log_error(e, {"operation": "get_user_usage", "user_id": user_id})
            raise

    def _create_default_usage_limits_for_user(self, user_id: str) -> UsageLimit:
        """Create default usage limits for a new user (assumes free tier)."""
        try:
            now = datetime.now(timezone.utc)

            # Default to free tier
            tier_config = self.usage_config["free"]
            daily_limit = tier_config["daily_limit"]

            usage = UsageLimit(
                tier="free",
                current_daily_usage=0,
                reset_daily_at=now.replace(hour=0, minute=0, second=0, microsecond=0),
            )

            # Save to database
            success = self.repository.update_usage_limits(user_id, usage)
            if not success:
                logger.log_error(
                    Exception("Failed to create default usage limits"),
                    {"user_id": user_id, "tier": "free"},
                )

            return usage

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_create_default_usage_limits_for_user",
                    "user_id": user_id,
                },
            )
            raise

    def _create_default_usage_limits(self, user_id: str, tier: UserTier) -> None:
        """Create default usage limits for a user."""
        try:
            now = datetime.now(timezone.utc)

            # Get limits based on tier
            tier_config = self.usage_config.get(tier.value, self.usage_config["free"])
            daily_limit = tier_config["daily_limit"]

            usage = UsageLimit(
                tier=tier.value,
                current_daily_usage=0,
                reset_daily_at=now.replace(hour=0, minute=0, second=0, microsecond=0),
            )

            success = self.repository.update_usage_limits(user_id, usage)
            if not success:
                logger.log_error(
                    Exception("Failed to create default usage limits"),
                    {"user_id": user_id, "tier": tier.value},
                )

        except Exception as e:
            logger.log_error(
                e, {"operation": "_create_default_usage_limits", "user_id": user_id}
            )

    @tracer.trace_method("update_user")
    def update_user(self, user: User) -> bool:
        """Update user information."""
        try:
            user.updated_at = datetime.now(timezone.utc)
            success = self.repository.update_user(user)

            if success:
                logger.log_business_event(
                    "user_updated",
                    {
                        "user_id": user.user_id,
                        "tier": user.tier.value,
                        "status": user.status.value,
                    },
                )

            return success

        except Exception as e:
            logger.log_error(e, {"operation": "update_user", "user_id": user.user_id})
            return False

    @tracer.trace_method("increment_usage_with_check")
    def increment_usage_with_check(self, user_id: str) -> None:
        """Increment usage after checking limits (for translation operations)."""
        try:
            # Get usage data and check limits
            usage_response = self.get_user_usage(user_id)

            # Check if limits are exceeded
            if usage_response.daily_remaining <= 0:
                raise UsageLimitExceededError(
                    "daily",
                    usage_response.daily_used,
                    usage_response.daily_limit,
                )

            # Get the underlying UsageLimit object for incrementing
            usage = self.repository.get_usage_limits(user_id)
            if not usage:
                # This shouldn't happen since get_user_usage would have created it
                raise ValueError(f"No usage data found for user {user_id}")

            # Then increment usage (pass the usage data to avoid duplicate fetch)
            self.increment_usage(user_id, usage)

        except Exception as e:
            logger.log_error(
                e, {"operation": "increment_usage_with_check", "user_id": user_id}
            )
            raise

    @tracer.trace_method("increment_usage")
    def increment_usage(self, user_id: str, usage: UsageLimit) -> None:
        """Increment user usage (assumes limits already checked)."""
        # Increment usage
        usage.current_daily_usage += 1

        # Update reset times if needed
        now = datetime.now(timezone.utc)
        if not usage.reset_daily_at or now.date() > usage.reset_daily_at.date():
            usage.reset_daily_at = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            usage.current_daily_usage = 1

        success = self.repository.update_usage_limits(user_id, usage)
        if not success:
            logger.log_error(
                Exception("Failed to update usage limits"),
                {"user_id": user_id},
            )

    @tracer.trace_method("upgrade_user_tier")
    def upgrade_user_tier(self, user_id: str, new_tier: UserTier) -> bool:
        """Upgrade user to a new tier."""
        try:
            user = self.repository.get_user(user_id)
            if not user:
                return False

            user.tier = new_tier
            user.updated_at = datetime.now(timezone.utc)

            if new_tier == UserTier.PREMIUM:
                user.subscription_start_date = datetime.now(timezone.utc)
                # Set subscription end date (e.g., 1 year from now)
                user.subscription_end_date = datetime.now(timezone.utc).replace(
                    year=datetime.now(timezone.utc).year + 1
                )

            success = self.repository.update_user(user)

            if success:
                logger.log_business_event(
                    "user_tier_upgraded",
                    {
                        "user_id": user_id,
                        "new_tier": new_tier.value,
                    },
                )

            return success

        except Exception as e:
            logger.log_error(e, {"operation": "upgrade_user_tier", "user_id": user_id})
            return False

    @tracer.trace_method("suspend_user")
    def suspend_user(self, user_id: str) -> bool:
        """Suspend a user account."""
        try:
            user = self.repository.get_user(user_id)
            if not user:
                return False

            user.status = UserStatus.SUSPENDED
            user.updated_at = datetime.now(timezone.utc)

            success = self.repository.update_user(user)

            if success:
                logger.log_business_event(
                    "user_suspended",
                    {
                        "user_id": user_id,
                    },
                )

            return success

        except Exception as e:
            logger.log_error(e, {"operation": "suspend_user", "user_id": user_id})
            return False

    @tracer.trace_method("delete_user")
    def delete_user(self, user_id: str) -> bool:
        """Delete a user and all associated data."""
        try:
            success = self.repository.delete_user(user_id)

            if success:
                logger.log_business_event(
                    "user_deleted",
                    {
                        "user_id": user_id,
                    },
                )

            return success

        except Exception as e:
            logger.log_error(e, {"operation": "delete_user", "user_id": user_id})
            return False
