"""User repository for user-related data operations."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..models.users import User, UserUsage, UserTier, UserStatus
from ..models.translations import UsageLimit
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.aws_services import aws_services
from ..utils.config import get_config


class UserRepository:
    """Repository for user data operations."""

    def __init__(self) -> None:
        """Initialize user repository."""
        self.config = get_config()
        self.table_name = self.config.get_database_config()["users_table"]
        self.table = aws_services.get_table(self.table_name)

    @tracer.trace_database_operation("create", "users")
    def create_user(self, user: User) -> bool:
        """Create a new user record."""
        try:
            item = {
                "PK": f"USER#{user.user_id}",
                "SK": "PROFILE",
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "tier": user.tier.value,
                "status": user.status.value,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            self.table.put_item(Item=item)
            logger.log_business_event(
                "user_created",
                {
                    "user_id": user.user_id,
                    "username": user.username,
                    "tier": user.tier.value,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_user",
                    "user_id": user.user_id,
                },
            )
            return False

    @tracer.trace_database_operation("get", "users")
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return User(
                user_id=item["user_id"],
                username=item["username"],
                email=item.get("email"),
                tier=UserTier(item["tier"]),
                status=UserStatus(item["status"]),
                total_translations_used=item.get("total_translations_used", 0),
                last_translation_date=(
                    datetime.fromisoformat(item["last_translation_date"])
                    if item.get("last_translation_date")
                    else None
                ),
                subscription_start_date=(
                    datetime.fromisoformat(item["subscription_start_date"])
                    if item.get("subscription_start_date")
                    else None
                ),
                subscription_end_date=(
                    datetime.fromisoformat(item["subscription_end_date"])
                    if item.get("subscription_end_date")
                    else None
                ),
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=datetime.fromisoformat(item["updated_at"]),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_user",
                    "user_id": user_id,
                },
            )
            return None

    @tracer.trace_database_operation("update", "users")
    def update_user(self, user: User) -> bool:
        """Update user record."""
        try:
            item = {
                "PK": f"USER#{user.user_id}",
                "SK": "PROFILE",
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "tier": user.tier.value,
                "status": user.status.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            self.table.put_item(Item=item)
            logger.log_business_event(
                "user_updated",
                {
                    "user_id": user.user_id,
                    "tier": user.tier.value,
                    "status": user.status.value,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_user",
                    "user_id": user.user_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "users")
    def update_usage_limits(self, user_id: str, usage: UsageLimit) -> bool:
        """Update user usage limits."""
        try:
            item = {
                "PK": f"USER#{user_id}",
                "SK": "USAGE#LIMITS",
                "tier": usage.tier,
                "current_daily_usage": usage.current_daily_usage,
                "reset_daily_at": (
                    usage.reset_daily_at.isoformat() if usage.reset_daily_at else None
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            logger.log_business_event(
                "usage_limits_updated",
                {
                    "user_id": user_id,
                    "daily_usage": usage.current_daily_usage,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_usage_limits",
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("get", "users")
    def get_usage_limits(self, user_id: str) -> Optional[UsageLimit]:
        """Get user usage limits."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "USAGE#LIMITS",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return UsageLimit(
                tier=item["tier"],
                current_daily_usage=item.get("current_daily_usage", 0),
                reset_daily_at=(
                    datetime.fromisoformat(item["reset_daily_at"])
                    if item.get("reset_daily_at")
                    else None
                ),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_usage_limits",
                    "user_id": user_id,
                },
            )
            return None

    @tracer.trace_database_operation("batch_get", "users")
    def get_user_and_usage(
        self, user_id: str
    ) -> tuple[Optional[User], Optional[UsageLimit]]:
        """Get both user profile and usage limits in one efficient operation."""
        try:
            # Use BatchGetItem to fetch both items in one call
            response = self.table.batch_get_item(
                RequestItems={
                    self.table.name: {
                        "Keys": [
                            {
                                "PK": f"USER#{user_id}",
                                "SK": "PROFILE",
                            },
                            {
                                "PK": f"USER#{user_id}",
                                "SK": "USAGE#LIMITS",
                            },
                        ]
                    }
                }
            )

            user_item = None
            usage_item = None

            # Parse the response
            for item in response.get("Responses", {}).get(self.table.name, []):
                if item.get("SK") == "PROFILE":
                    user_item = item
                elif item.get("SK") == "USAGE#LIMITS":
                    usage_item = item

            # Parse user
            user = None
            if user_item:
                user = User(
                    user_id=user_item["user_id"],
                    username=user_item["username"],
                    email=user_item.get("email"),
                    tier=UserTier(user_item["tier"]),
                    status=UserStatus(user_item["status"]),
                    total_translations_used=user_item.get("total_translations_used", 0),
                    last_translation_date=(
                        datetime.fromisoformat(user_item["last_translation_date"])
                        if user_item.get("last_translation_date")
                        else None
                    ),
                    subscription_start_date=(
                        datetime.fromisoformat(user_item["subscription_start_date"])
                        if user_item.get("subscription_start_date")
                        else None
                    ),
                    subscription_end_date=(
                        datetime.fromisoformat(user_item["subscription_end_date"])
                        if user_item.get("subscription_end_date")
                        else None
                    ),
                    created_at=datetime.fromisoformat(user_item["created_at"]),
                    updated_at=datetime.fromisoformat(user_item["updated_at"]),
                )

            # Parse usage limits
            usage_limits = None
            if usage_item:
                usage_limits = UsageLimit(
                    tier=usage_item["tier"],
                    current_daily_usage=usage_item.get("current_daily_usage", 0),
                    reset_daily_at=(
                        datetime.fromisoformat(usage_item["reset_daily_at"])
                        if usage_item.get("reset_daily_at")
                        else None
                    ),
                )

            return user, usage_limits

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_user_and_usage",
                    "user_id": user_id,
                },
            )
            return None, None

    @tracer.trace_database_operation("delete", "users")
    def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data."""
        try:
            # Delete user profile
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                }
            )

            # Delete usage limits
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "USAGE#LIMITS",
                }
            )

            logger.log_business_event(
                "user_deleted",
                {
                    "user_id": user_id,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "delete_user",
                    "user_id": user_id,
                },
            )
            return False
