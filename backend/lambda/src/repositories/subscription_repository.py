"""Subscription repository for subscription data operations."""

from datetime import datetime, timezone
from typing import Optional

from models.subscriptions import (
    UserSubscription,
    SubscriptionProvider,
    SubscriptionStatus,
)
from utils.logging import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service


class SubscriptionRepository:
    """Repository for subscription data operations."""

    def __init__(self) -> None:
        """Initialize subscription repository."""
        self.config_service = get_config_service()
        self.table_name = self.config_service._get_env_var('USERS_TABLE')
        self.table = aws_services.get_table(self.table_name)

    @tracer.trace_database_operation("create", "subscriptions")
    def create_subscription(self, subscription: UserSubscription) -> bool:
        """Create a new subscription record."""
        try:
            item = {
                "PK": f"USER#{subscription.user_id}",
                "SK": "SUBSCRIPTION#ACTIVE",
                "user_id": subscription.user_id,
                "provider": subscription.provider,
                "transaction_id": subscription.transaction_id,
                "status": subscription.status,
                "start_date": subscription.start_date.isoformat(),
                "end_date": (
                    subscription.end_date.isoformat() if subscription.end_date else None
                ),
                "created_at": subscription.created_at.isoformat(),
                "updated_at": subscription.updated_at.isoformat(),
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            logger.log_business_event(
                "subscription_created",
                {
                    "user_id": subscription.user_id,
                    "provider": subscription.provider,
                    "transaction_id": subscription.transaction_id,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_subscription",
                    "user_id": subscription.user_id,
                },
            )
            return False

    @tracer.trace_database_operation("get", "subscriptions")
    def get_active_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """Get user's active subscription."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "SUBSCRIPTION#ACTIVE",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return UserSubscription(
                user_id=item["user_id"],
                provider=SubscriptionProvider(item["provider"]),
                transaction_id=item["transaction_id"],
                status=SubscriptionStatus(item["status"]),
                start_date=datetime.fromisoformat(item["start_date"]),
                end_date=(
                    datetime.fromisoformat(item["end_date"])
                    if item.get("end_date")
                    else None
                ),
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=datetime.fromisoformat(item["updated_at"]),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_active_subscription",
                    "user_id": user_id,
                },
            )
            return None

    @tracer.trace_database_operation("update", "subscriptions")
    def update_subscription(self, subscription: UserSubscription) -> bool:
        """Update subscription record."""
        try:
            item = {
                "PK": f"USER#{subscription.user_id}",
                "SK": "SUBSCRIPTION#ACTIVE",
                "user_id": subscription.user_id,
                "provider": subscription.provider,
                "transaction_id": subscription.transaction_id,
                "status": subscription.status,
                "start_date": subscription.start_date.isoformat(),
                "end_date": (
                    subscription.end_date.isoformat() if subscription.end_date else None
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            logger.log_business_event(
                "subscription_updated",
                {
                    "user_id": subscription.user_id,
                    "provider": subscription.provider,
                    "status": subscription.status,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_subscription",
                    "user_id": subscription.user_id,
                },
            )
            return False

    @tracer.trace_database_operation("delete", "subscriptions")
    def cancel_subscription(self, user_id: str) -> bool:
        """Cancel user's active subscription."""
        try:
            # First get the current subscription to archive it
            current_subscription = self.get_active_subscription(user_id)
            if not current_subscription:
                logger.log_business_event(
                    "subscription_cancel_attempt_no_subscription",
                    {"user_id": user_id},
                )
                return True  # No subscription to cancel

            # Archive the subscription
            archive_item = {
                "PK": f"USER#{user_id}",
                "SK": f"SUBSCRIPTION#HISTORY#{current_subscription.transaction_id}",
                "user_id": user_id,
                "provider": current_subscription.provider,
                "transaction_id": current_subscription.transaction_id,
                "status": "cancelled",
                "start_date": current_subscription.start_date.isoformat(),
                "end_date": (
                    current_subscription.end_date.isoformat()
                    if current_subscription.end_date
                    else None
                ),
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "created_at": current_subscription.created_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            # Remove None values
            archive_item = {k: v for k, v in archive_item.items() if v is not None}

            # Delete active subscription and create archive
            with self.table.batch_writer() as batch:
                batch.delete_item(
                    Key={
                        "PK": f"USER#{user_id}",
                        "SK": "SUBSCRIPTION#ACTIVE",
                    }
                )
                batch.put_item(Item=archive_item)

            logger.log_business_event(
                "subscription_cancelled",
                {
                                    "user_id": user_id,
                "provider": current_subscription.provider,
                    "transaction_id": current_subscription.transaction_id,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "cancel_subscription",
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("get", "subscriptions")
    def find_by_transaction_id(self, transaction_id: str) -> Optional[UserSubscription]:
        """Find subscription by transaction ID (requires GSI)."""
        try:
            # TODO: Implement GSI query on transaction_id
            # For now, this is a placeholder
            logger.log_business_event(
                "subscription_lookup_by_transaction",
                {"transaction_id": transaction_id},
            )
            return None

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "find_by_transaction_id",
                    "transaction_id": transaction_id,
                },
            )
            return None
