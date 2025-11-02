"""User service for user management and usage tracking."""

from typing import Optional

from models.users import (
    User,
    UserTier,
    UserStatus,
    UserUsageResponse,
)
from models.translations import UsageLimit
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.config import get_config_service, UsageLimitsConfig, CognitoConfig
from utils.exceptions import ValidationError
from utils.timezone_utils import get_central_midnight_tomorrow, is_new_day_central_time
from utils.aws_services import get_cognito_client
from repositories.user_repository import UserRepository
from repositories.slang_term_repository import SlangTermRepository


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
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            tier=tier,
            status=UserStatus.ACTIVE,
        )

        self.repository.create_user(user)

        logger.log_business_event(
            "user_created",
            {
                "user_id": user_id,
                "username": username,
                "tier": tier,
            },
        )

        return user

    @tracer.trace_method("get_user")
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.repository.get_user(user_id)

    @tracer.trace_method("get_user_usage")
    def get_user_usage(self, user_id: str) -> UserUsageResponse:
        """Get user usage statistics for API response (dynamic data)."""
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
            current_max_text_length=(
                self.usage_config.free_max_text_length
                if usage_limits.tier == UserTier.FREE
                else self.usage_config.premium_max_text_length
            ),
            free_tier_max_length=self.usage_config.free_max_text_length,
            premium_tier_max_length=self.usage_config.premium_max_text_length,
            free_daily_limit=self.usage_config.free_daily_translations,
            premium_daily_limit=self.usage_config.premium_daily_translations,
        )

    def _create_default_usage_limits(self, user_id: str, tier: UserTier) -> UsageLimit:
        """Create default usage limits for a user."""
        # Use Central Time midnight for reset
        tomorrow_start = get_central_midnight_tomorrow()

        usage = UsageLimit(
            tier=tier,
            daily_used=0,
            reset_daily_at=tomorrow_start,
        )

        self.repository.update_usage_limits(user_id, usage)

        return usage

    @tracer.trace_method("increment_usage")
    def increment_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> None:
        """Atomically increment user usage (assumes limits already checked)."""
        self.repository.increment_usage(user_id, tier)

    @tracer.trace_method("reset_daily_usage")
    def reset_daily_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> None:
        """Reset daily usage counter to 0."""
        self.repository.reset_daily_usage(user_id, tier)

    @tracer.trace_method("upgrade_user_tier")
    def upgrade_user_tier(self, user_id: str, new_tier: UserTier) -> None:
        """Upgrade user to a new tier."""
        user = self.repository.get_user(user_id)
        if not user:
            raise ValidationError(f"User not found: {user_id}")

        user.tier = new_tier

        # Update user profile
        self.repository.update_user(user)

        # CRITICAL: Also update the usage limits tier to keep them in sync
        # Usage limits are the source of truth for performance (frequent get_user_usage calls)
        usage_limits = self.repository.get_usage_limits(user_id)
        if usage_limits:
            usage_limits.tier = new_tier
            self.repository.update_usage_limits(user_id, usage_limits)
        else:
            # Create default usage limits with new tier
            self._create_default_usage_limits(user_id, new_tier)

        # Reset quiz daily limit when upgrading to PREMIUM (allows immediate unlimited access)
        if new_tier == UserTier.PREMIUM:
            deleted = self.repository.delete_daily_quiz_count(user_id)
            if deleted:
                logger.log_business_event(
                    "quiz_limit_reset_on_upgrade",
                    {
                        "user_id": user_id,
                    },
                )
            # Note: We don't fail upgrade if quiz limit deletion fails (it's not critical)

        logger.log_business_event(
            "user_tier_upgraded",
            {
                "user_id": user_id,
                "new_tier": new_tier,
            },
        )

    @tracer.trace_method("suspend_user")
    def suspend_user(self, user_id: str) -> None:
        """Suspend a user account."""
        user = self.repository.get_user(user_id)
        if not user:
            raise ValidationError(f"User not found: {user_id}")

        user.status = UserStatus.SUSPENDED

        self.repository.update_user(user)

        logger.log_business_event(
            "user_suspended",
            {
                "user_id": user_id,
            },
        )

    @tracer.trace_method("downgrade_user_tier")
    def downgrade_user_tier(self, user_id: str, new_tier: UserTier) -> None:
        """Downgrade user to a new tier (typically FREE)."""
        user = self.repository.get_user(user_id)
        if not user:
            raise ValidationError(f"User not found: {user_id}")

        user.tier = new_tier

        # Update user profile
        self.repository.update_user(user)

        # CRITICAL: Also update the usage limits tier to keep them in sync
        # Usage limits are the source of truth for performance (frequent get_user_usage calls)
        usage_limits = self.repository.get_usage_limits(user_id)
        if usage_limits:
            usage_limits.tier = new_tier
            self.repository.update_usage_limits(user_id, usage_limits)
        else:
            # Create default usage limits with new tier
            self._create_default_usage_limits(user_id, new_tier)

        logger.log_business_event(
            "user_tier_downgraded",
            {
                "user_id": user_id,
                "new_tier": new_tier,
            },
        )

    @tracer.trace_method("delete_user")
    def delete_user(self, user_id: str) -> None:
        """Delete a user and all associated data from both DynamoDB and Cognito."""
        # Step 1: Delete quiz data from termsTable (sessions and history)
        quiz_repo = SlangTermRepository()
        quiz_repo.delete_user_quiz_data(user_id)

        # Step 2: Delete user data from DynamoDB (includes quiz daily counts)
        self.repository.delete_user(user_id)

        # Step 3: Delete user from Cognito
        try:
            cognito_config = self.config_service.get_config(CognitoConfig)
            cognito_client = get_cognito_client()

            cognito_client.admin_delete_user(
                UserPoolId=cognito_config.user_pool_id, Username=user_id
            )

            logger.log_business_event(
                "cognito_user_deleted",
                {
                    "user_id": user_id,
                    "user_pool_id": cognito_config.user_pool_id,
                },
            )

        except Exception as cognito_error:
            # Log the error but don't fail the entire deletion
            # The user data is already deleted from DynamoDB
            logger.log_error(
                cognito_error,
                {
                    "operation": "delete_cognito_user",
                    "user_id": user_id,
                    "note": "User data deleted from DynamoDB but Cognito deletion failed",
                },
            )
            # Continue - we don't want to fail the entire deletion if Cognito fails

        logger.log_business_event(
            "user_deleted",
            {
                "user_id": user_id,
            },
        )

    @tracer.trace_method("increment_slang_submitted")
    def increment_slang_submitted(self, user_id: str) -> None:
        """
        Increment the slang submitted count for a user.

        Args:
            user_id: The user ID
        """
        success = self.repository.increment_slang_submitted(user_id)
        if success:
            logger.log_business_event(
                "slang_submitted_count_incremented",
                {"user_id": user_id},
            )

    @tracer.trace_method("increment_slang_approved")
    def increment_slang_approved(self, user_id: str) -> None:
        """
        Increment the slang approved count for a user.

        Args:
            user_id: The user ID
        """
        success = self.repository.increment_slang_approved(user_id)
        if success:
            logger.log_business_event(
                "slang_approved_count_incremented",
                {"user_id": user_id},
            )
