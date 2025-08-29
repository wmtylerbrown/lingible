"""User service for user management and usage tracking."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..models.users import User, UserTier, UserStatus, UserUsage
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
    def create_user(self, user_id: str, username: str, email: str, tier: UserTier = UserTier.FREE) -> User:
        """Create a new user."""
        try:
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                tier=tier,
                status=UserStatus.ACTIVE,
                monthly_translations_used=0,
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

    @tracer.trace_method("check_usage_limits")
    def check_usage_limits(self, user_id: str) -> None:
        """Check if user has exceeded usage limits."""
        usage = self.repository.get_usage_limits(user_id)

        if not usage:
            # Create default usage limits for new user
            usage = UsageLimit(
                daily_limit=self.usage_config["free"]["daily_limit"],
                monthly_limit=self.usage_config["free"]["monthly_limit"],
                current_daily_usage=0,
                current_monthly_usage=0,
                reset_daily_at=None,
                reset_monthly_at=None,
            )

        # Check if limits are exceeded
        if usage.current_daily_usage >= usage.daily_limit:
            raise UsageLimitExceededError(
                "daily",
                usage.current_daily_usage,
                usage.daily_limit,
            )

        if usage.current_monthly_usage >= usage.monthly_limit:
            raise UsageLimitExceededError(
                "monthly",
                usage.current_monthly_usage,
                usage.monthly_limit,
            )

    @tracer.trace_method("increment_usage")
    def increment_usage(self, user_id: str) -> None:
        """Increment user usage after a translation."""
        usage = self.repository.get_usage_limits(user_id)
        
        if not usage:
            usage = UsageLimit(
                daily_limit=self.usage_config["free"]["daily_limit"],
                monthly_limit=self.usage_config["free"]["monthly_limit"],
                current_daily_usage=0,
                current_monthly_usage=0,
                reset_daily_at=None,
                reset_monthly_at=None,
            )

        # Increment usage
        usage.current_daily_usage += 1
        usage.current_monthly_usage += 1

        # Update reset times if needed
        now = datetime.now(timezone.utc)
        if not usage.reset_daily_at or now.date() > usage.reset_daily_at.date():
            usage.reset_daily_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
            usage.current_daily_usage = 1

        if not usage.reset_monthly_at or now.month != usage.reset_monthly_at.month:
            usage.reset_monthly_at = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            usage.current_monthly_usage = 1

        success = self.repository.update_usage_limits(user_id, usage)
        if not success:
            logger.log_error(
                Exception("Failed to update usage limits"),
                {"user_id": user_id},
            )

    @tracer.trace_method("get_usage_limits")
    def get_usage_limits(self, user_id: str) -> Optional[UsageLimit]:
        """Get user's current usage limits."""
        return self.repository.get_usage_limits(user_id)

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
                user.subscription_end_date = datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1)

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
