"""User repository for user-related data operations."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from models.users import User, UserTier
from models.translations import UsageLimit
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service
from utils.timezone_utils import (
    get_central_midnight_tomorrow,
    get_central_midnight_today,
)
from utils.exceptions import SystemError


class UserRepository:
    """Repository for user data operations."""

    def __init__(self) -> None:
        """Initialize user repository."""
        self.config_service = get_config_service()
        self.table_name = self.config_service._get_env_var("USERS_TABLE")
        self.table = aws_services.get_table(self.table_name)

    @tracer.trace_database_operation("create", "users")
    def create_user(self, user: User) -> None:
        """Create a new user record."""
        try:
            # Convert User object to DynamoDB item format
            item = {
                "PK": f"USER#{user.user_id}",
                "SK": "PROFILE",
                **user.model_dump(mode="json"),  # Serialize the User object to dict
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            self.table.put_item(Item=item)
            # Don't log every user creation - it's a routine operation

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_user",
                    "user_id": user.user_id,
                },
            )
            raise SystemError(f"Failed to create user {user.user_id}")

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
            return User(**item)

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
    def update_user(self, user: User) -> None:
        """Update user record."""
        try:
            # Update the updated_at timestamp
            user.updated_at = datetime.now(timezone.utc)

            # Convert User object to DynamoDB item format
            item = {
                "PK": f"USER#{user.user_id}",
                "SK": "PROFILE",
                **user.model_dump(mode="json"),  # Serialize the User object to dict
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            self.table.put_item(Item=item)
            # Don't log every user update - it's a routine operation

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_user",
                    "user_id": user.user_id,
                },
            )
            raise SystemError(f"Failed to update user {user.user_id}")

    @tracer.trace_database_operation("update", "users")
    def update_usage_limits(self, user_id: str, usage: UsageLimit) -> None:
        """Update user usage limits."""
        try:
            item = {
                "PK": f"USER#{user_id}",
                "SK": "USAGE#LIMITS",
                "tier": usage.tier,
                "daily_used": usage.daily_used,
                "reset_daily_at": usage.reset_daily_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            # Don't log every usage limit update - it's a routine operation

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_usage_limits",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to update usage limits for user {user_id}")

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
            # Ensure reset_daily_at exists, create default if missing
            reset_daily_at = item.get("reset_daily_at")
            if not reset_daily_at:
                # Create default reset date (tomorrow at midnight Central Time)
                tomorrow_start = get_central_midnight_tomorrow()
                reset_daily_at = tomorrow_start.isoformat()

            return UsageLimit(
                tier=UserTier(item["tier"]),
                daily_used=item.get("daily_used", 0),
                reset_daily_at=datetime.fromisoformat(reset_daily_at),
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
    def increment_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> None:
        """Atomically increment usage counter and reset if needed."""
        try:
            now = datetime.now(timezone.utc)
            today_start = get_central_midnight_today()
            tomorrow_start = get_central_midnight_tomorrow()

            # First, try to increment usage (this will work if it's the same day)
            try:
                self.table.update_item(
                    Key={
                        "PK": f"USER#{user_id}",
                        "SK": "USAGE#LIMITS",
                    },
                    UpdateExpression="SET daily_used = if_not_exists(daily_used, :zero) + :one, reset_daily_at = if_not_exists(reset_daily_at, :tomorrow_start), updated_at = :updated_at, tier = if_not_exists(tier, :tier)",
                    ExpressionAttributeValues={
                        ":zero": 0,
                        ":one": 1,
                        ":today_start": today_start.isoformat(),
                        ":tomorrow_start": tomorrow_start.isoformat(),
                        ":updated_at": now.isoformat(),
                        ":tier": tier,
                    },
                    ConditionExpression="attribute_not_exists(reset_daily_at) OR reset_daily_at > :today_start",
                    ReturnValues="UPDATED_NEW",
                )

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
                        ":tier": tier,
                    },
                    ReturnValues="UPDATED_NEW",
                )

                # Successfully reset and incremented (new day)
                # Don't log every usage increment - it's a routine operation

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_usage",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to increment usage for user {user_id}")

    @tracer.trace_database_operation("update", "users")
    def reset_daily_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> None:
        """Reset daily usage counter to 0."""
        try:
            now = datetime.now(timezone.utc)
            tomorrow_start = get_central_midnight_tomorrow()

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
                    ":tier": tier,
                },
            )

            # Don't log every usage reset - it's a routine operation

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "reset_daily_usage",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to reset usage for user {user_id}")

    @tracer.trace_database_operation("delete", "users")
    def delete_user(self, user_id: str) -> None:
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

            # Delete all quiz daily count items (query and delete all QUIZ_DAILY# items)
            try:
                # Query for all quiz daily items for this user
                response = self.table.query(
                    KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                    ExpressionAttributeValues={
                        ":pk": f"USER#{user_id}",
                        ":sk_prefix": "QUIZ_DAILY#",
                    },
                )
                quiz_items = response.get("Items", [])
                for item in quiz_items:
                    self.table.delete_item(
                        Key={
                            "PK": item["PK"],
                            "SK": item["SK"],
                        }
                    )
                if quiz_items:
                    logger.log_business_event(
                        "quiz_daily_count_items_deleted",
                        {
                            "user_id": user_id,
                            "deleted_count": len(quiz_items),
                        },
                    )
            except Exception as e:
                # Log but don't fail user deletion if quiz cleanup fails
                logger.log_error(
                    e,
                    {
                        "operation": "delete_quiz_daily_counts",
                        "user_id": user_id,
                    },
                )

            logger.log_business_event(
                "user_deleted",
                {
                    "user_id": user_id,
                },
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "delete_user",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to delete user {user_id}")

    @tracer.trace_database_operation("get", "daily_quiz_count")
    def get_daily_quiz_count(self, user_id: str, date: str) -> int:
        """Get number of quiz questions answered today."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{date}",
                }
            )

            if "Item" in response:
                return response["Item"].get("quiz_count", 0)
            return 0

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_daily_quiz_count",
                    "user_id": user_id,
                    "date": date,
                },
            )
            return 0

    @tracer.trace_database_operation("update", "daily_quiz_count")
    def increment_daily_quiz_count(self, user_id: str) -> int:
        """Increment and return daily quiz count. Creates item if needed with TTL (48h after date)."""
        try:
            today = datetime.now(timezone.utc).date()
            today_str = today.isoformat()

            # Calculate TTL: 48 hours after the date (e.g., if date is 2024-12-19, TTL = 2024-12-21 00:00 UTC)
            # Convert date string to datetime at midnight UTC, then add 48 hours
            date_obj = datetime.strptime(today_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            ttl_timestamp = int((date_obj + timedelta(hours=48)).timestamp())

            response = self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{today_str}",
                },
                UpdateExpression="ADD quiz_count :inc SET last_quiz_at = :timestamp, #ttl = :ttl",
                ExpressionAttributeNames={
                    "#ttl": "ttl",  # ttl is a reserved word in DynamoDB
                },
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                    ":ttl": ttl_timestamp,
                },
                ReturnValues="UPDATED_NEW",
            )

            return response["Attributes"].get("quiz_count", 1)

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_daily_quiz_count",
                    "user_id": user_id,
                },
            )
            return 1

    @tracer.trace_database_operation("delete", "daily_quiz_count")
    def delete_daily_quiz_count(self, user_id: str) -> bool:
        """Delete the quiz daily count item for today."""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{today}",
                }
            )
            return True
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "delete_daily_quiz_count",
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "users")
    def increment_slang_submitted(self, user_id: str) -> bool:
        """
        Increment the slang submitted count for a user.

        Args:
            user_id: The user ID

        Returns:
            True if increment was successful
        """
        try:
            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                },
                UpdateExpression="SET slang_submitted_count = if_not_exists(slang_submitted_count, :zero) + :inc, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_slang_submitted",
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "users")
    def increment_slang_approved(self, user_id: str) -> bool:
        """
        Increment the slang approved count for a user.

        Args:
            user_id: The user ID

        Returns:
            True if increment was successful
        """
        try:
            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                },
                UpdateExpression="SET slang_approved_count = if_not_exists(slang_approved_count, :zero) + :inc, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_slang_approved",
                    "user_id": user_id,
                },
            )
            return False
