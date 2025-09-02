"""User repository for user-related data operations."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from models.users import User, UserTier, UserStatus
from models.translations import UsageLimit
from utils.logging import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service, TableConfig


class UserRepository:
    """Repository for user data operations."""

    def __init__(self) -> None:
        """Initialize user repository."""
        self.config_service = get_config_service()
        users_table_config = self.config_service.get_config(TableConfig, "users")
        self.table_name = users_table_config.name
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
                "tier": user.tier,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            self.table.put_item(Item=item)
            # Don't log every user creation - it's a routine operation
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
                "tier": user.tier,
                "status": user.status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            self.table.put_item(Item=item)
            # Don't log every user update - it's a routine operation
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
                "tier": usage.tier.value,
                "daily_used": usage.daily_used,
                "reset_daily_at": (
                    usage.reset_daily_at.isoformat() if usage.reset_daily_at else None
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            # Don't log every usage limit update - it's a routine operation
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
                tier=UserTier(item["tier"]),
                daily_used=item.get("daily_used", 0),
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

    @tracer.trace_database_operation("update", "users")
    def increment_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> bool:
        """Atomically increment usage counter and reset if needed."""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)

            # First, try to increment usage (this will work if it's the same day)
            try:
                self.table.update_item(
                    Key={
                        "PK": f"USER#{user_id}",
                        "SK": "USAGE#LIMITS",
                    },
                    UpdateExpression="SET daily_used = if_not_exists(daily_used, 0) + :one, updated_at = :updated_at, tier = if_not_exists(tier, :tier)",
                    ExpressionAttributeValues={
                        ":one": 1,
                        ":today_start": today_start.isoformat(),
                        ":updated_at": now.isoformat(),
                        ":tier": tier.value,
                    },
                    ConditionExpression="attribute_not_exists(reset_daily_at) OR reset_daily_at > :today_start",
                    ReturnValues="UPDATED_NEW",
                )

                return True

            except Exception:
                # Condition failed means it's a new day, so reset and set to 1
                self.table.update_item(
                    Key={
                        "PK": f"USER#{user_id}",
                        "SK": "USAGE#LIMITS",
                    },
                    UpdateExpression="SET daily_used = :one, reset_daily_at = :tomorrow_start, updated_at = :updated_at, tier = if_not_exists(tier, :tier)",
                    ExpressionAttributeValues={
                        ":one": 1,
                        ":tomorrow_start": tomorrow_start.isoformat(),
                        ":updated_at": now.isoformat(),
                        ":tier": tier.value,
                    },
                    ReturnValues="UPDATED_NEW",
                )

                # Successfully reset and incremented (new day)
                # Don't log every usage increment - it's a routine operation
                return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_usage",
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "users")
    def reset_daily_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> bool:
        """Reset daily usage counter to 0."""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)

            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "USAGE#LIMITS",
                },
                UpdateExpression="SET daily_used = :zero, reset_daily_at = :tomorrow_start, updated_at = :updated_at, tier = if_not_exists(tier, :tier)",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":tomorrow_start": tomorrow_start.isoformat(),
                    ":updated_at": now.isoformat(),
                    ":tier": tier.value,
                },
            )

            # Don't log every usage reset - it's a routine operation
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "reset_daily_usage",
                    "user_id": user_id,
                },
            )
            return False

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
