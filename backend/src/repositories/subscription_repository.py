"""Subscription repository for DynamoDB operations."""

from typing import Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

from ..models.subscriptions import (
    Subscription,
    SubscriptionHistory,
    SubscriptionStatus,
)
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.aws_services import aws_services
from ..utils.config import get_config


@dataclass
class QueryResult:
    """Query result with pagination."""

    items: List[Subscription]
    last_evaluated_key: Optional[dict] = None
    count: int = 0
    scanned_count: int = 0


class SubscriptionRepository:
    """Repository for subscription data operations."""

    def __init__(self):
        """Initialize subscription repository."""
        self.config = get_config()
        self.table_name = self.config.get_database_config()["users_table"]
        self.table = aws_services.get_table(self.table_name)

    @tracer.trace_method("get_subscription")
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by ID."""
        try:
            # Query for subscription with the given ID
            response = self.table.query(
                IndexName="SKIndex",  # Assuming we have a GSI on SK
                KeyConditionExpression="SK = :sk",
                ExpressionAttributeValues={":sk": f"SUBSCRIPTION#{subscription_id}"},
                Limit=1
            )

            if not response.get("Items"):
                return None

            item = response["Items"][0]
            return Subscription(**item)

        except Exception as e:
            logger.log_error(e, {"operation": "get_subscription", "subscription_id": subscription_id})
            return None

    @tracer.trace_method("get_active_subscription")
    def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get the active subscription for a user."""
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
                ExpressionAttributeValues={
                    ":pk": f"USER#{user_id}",
                    ":sk": "SUBSCRIPTION#"
                },
                FilterExpression="#status = :active",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":active": SubscriptionStatus.ACTIVE.value},
                Limit=1
            )

            if not response.get("Items"):
                return None

            item = response["Items"][0]
            return Subscription(**item)

        except Exception as e:
            logger.log_error(e, {"operation": "get_active_subscription", "user_id": user_id})
            return None

    @tracer.trace_method("get_user_subscriptions")
    def get_user_subscriptions(self, user_id: str) -> List[Subscription]:
        """Get all subscriptions for a user."""
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
                ExpressionAttributeValues={
                    ":pk": f"USER#{user_id}",
                    ":sk": "SUBSCRIPTION#"
                }
            )

            subscriptions = []
            for item in response.get("Items", []):
                subscriptions.append(Subscription(**item))

            return subscriptions

        except Exception as e:
            logger.log_error(e, {"operation": "get_user_subscriptions", "user_id": user_id})
            return []

    @tracer.trace_method("get_subscription_history")
    def get_subscription_history(self, user_id: str, limit: int = 10) -> List[SubscriptionHistory]:
        """Get subscription history for a user."""
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
                ExpressionAttributeValues={
                    ":pk": f"USER#{user_id}",
                    ":sk": "HISTORY#"
                },
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )

            history = []
            for item in response.get("Items", []):
                history.append(SubscriptionHistory(**item))

            return history

        except Exception as e:
            logger.log_error(e, {"operation": "get_subscription_history", "user_id": user_id})
            return []

    @tracer.trace_method("save_subscription_with_history")
    def save_subscription_with_history(
        self, subscription: Subscription, history: SubscriptionHistory, user=None
    ) -> bool:
        """Save subscription and history atomically."""
        try:
            items = []

            # Add subscription
            subscription_item = subscription.model_dump()
            subscription_item["PK"] = f"USER#{subscription.user_id}"
            subscription_item["SK"] = f"SUBSCRIPTION#{subscription.subscription_id}"
            items.append(subscription_item)

            # Add history
            history_item = history.model_dump()
            history_item["PK"] = f"USER#{history.user_id}"
            history_item["SK"] = f"HISTORY#{history.created_at.isoformat()}"
            items.append(history_item)

            # Add user update if provided
            if user:
                user_item = user.model_dump()
                user_item["PK"] = f"USER#{user.user_id}"
                user_item["SK"] = "PROFILE"
                items.append(user_item)

            # Use batch write for atomic operation
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)

            return True

        except Exception as e:
            logger.log_error(e, {
                "operation": "save_subscription_with_history",
                "user_id": subscription.user_id,
                "subscription_id": subscription.subscription_id
            })
            return False

    @tracer.trace_method("update_subscription_with_history")
    def update_subscription_with_history(
        self, subscription: Subscription, history: Optional[SubscriptionHistory] = None, user=None
    ) -> bool:
        """Update subscription and optionally add history atomically."""
        try:
            # Update subscription
            update_expression = "SET "
            expression_attribute_names = {}
            expression_attribute_values = {}

            # Build update expression dynamically
            updates = []
            for field, value in subscription.model_dump().items():
                if field not in ["PK", "SK", "subscription_id", "user_id"]:
                    attr_name = f"#{field}"
                    attr_value = f":{field}"
                    updates.append(f"{attr_name} = {attr_value}")
                    expression_attribute_names[attr_name] = field
                    expression_attribute_values[attr_value] = value

            update_expression += ", ".join(updates)

            # Update subscription
            self.table.update_item(
                Key={
                    "PK": f"USER#{subscription.user_id}",
                    "SK": f"SUBSCRIPTION#{subscription.subscription_id}"
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )

            # Add history if provided
            if history:
                history_item = history.model_dump()
                history_item["PK"] = f"USER#{history.user_id}"
                history_item["SK"] = f"HISTORY#{history.created_at.isoformat()}"

                self.table.put_item(Item=history_item)

            # Update user if provided
            if user:
                user_update_expression = "SET "
                user_expression_attribute_names = {}
                user_expression_attribute_values = {}

                user_updates = []
                for field, value in user.model_dump().items():
                    if field not in ["PK", "SK", "user_id"]:
                        attr_name = f"#{field}"
                        attr_value = f":{field}"
                        user_updates.append(f"{attr_name} = {attr_value}")
                        user_expression_attribute_names[attr_name] = field
                        user_expression_attribute_values[attr_value] = value

                user_update_expression += ", ".join(user_updates)

                self.table.update_item(
                    Key={
                        "PK": f"USER#{user.user_id}",
                        "SK": "PROFILE"
                    },
                    UpdateExpression=user_update_expression,
                    ExpressionAttributeNames=user_expression_attribute_names,
                    ExpressionAttributeValues=user_expression_attribute_values
                )

            return True

        except Exception as e:
            logger.log_error(e, {
                "operation": "update_subscription_with_history",
                "user_id": subscription.user_id,
                "subscription_id": subscription.subscription_id
            })
            return False

    @tracer.trace_method("delete_subscription")
    def delete_subscription(self, user_id: str, subscription_id: str) -> bool:
        """Delete a subscription."""
        try:
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"SUBSCRIPTION#{subscription_id}"
                }
            )
            return True

        except Exception as e:
            logger.log_error(e, {
                "operation": "delete_subscription",
                "user_id": user_id,
                "subscription_id": subscription_id
            })
            return False

    @tracer.trace_method("cleanup_expired_subscriptions")
    def cleanup_expired_subscriptions(self) -> int:
        """Clean up expired subscriptions."""
        try:
            # Query for expired subscriptions
            response = self.table.query(
                IndexName="StatusEndDateIndex",  # Assuming GSI on status and end_date
                KeyConditionExpression="#status = :expired AND #end_date < :now",
                ExpressionAttributeNames={
                    "#status": "status",
                    "#end_date": "end_date"
                },
                ExpressionAttributeValues={
                    ":expired": SubscriptionStatus.EXPIRED.value,
                    ":now": datetime.now(timezone.utc).isoformat()
                }
            )

            updated_count = 0
            for item in response.get("Items", []):
                # Update to cancelled status
                self.table.update_item(
                    Key={
                        "PK": item["PK"],
                        "SK": item["SK"]
                    },
                    UpdateExpression="SET #status = :cancelled, #updated_at = :now",
                    ExpressionAttributeNames={
                        "#status": "status",
                        "#updated_at": "updated_at"
                    },
                    ExpressionAttributeValues={
                        ":cancelled": SubscriptionStatus.CANCELLED.value,
                        ":now": datetime.now(timezone.utc).isoformat()
                    }
                )
                updated_count += 1

            return updated_count

        except Exception as e:
            logger.log_error(e, {"operation": "cleanup_expired_subscriptions"})
            return 0
