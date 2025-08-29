"""Cognito pre user deletion trigger handler for cleaning up user data."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from ..models.events import CognitoPreUserDeletionEvent
from ..services.user_service import UserService
from ..services.subscription_service import SubscriptionService
from ..utils.tracing import tracer
from ..utils.logging import logger
from datetime import datetime, timezone
from ..models.users import UserStatus


# Initialize services at module level for Lambda container reuse
user_service = UserService()
subscription_service = SubscriptionService()


@event_parser(model=CognitoPreUserDeletionEvent)
@tracer.trace_method("cognito_pre_user_deletion")
def pre_user_deletion_handler(
    event: CognitoPreUserDeletionEvent, context: LambdaContext
) -> CognitoPreUserDeletionEvent:
    """Clean up user data from DynamoDB before Cognito user deletion."""
    try:
        user_id = event.userName
        user_attributes = event.request.userAttributes

        logger.log_business_event(
            "cognito_user_deletion_started",
            {
                "user_id": user_id,
                "email": user_attributes.email,
            },
        )

        # Check if user exists in our system
        existing_user = user_service.get_user(user_id)
        if not existing_user:
            logger.log_business_event(
                "user_not_found_for_deletion",
                {"user_id": user_id},
            )
            return event

        # Cancel any active subscriptions
        active_subscription = subscription_service.get_active_subscription(user_id)
        if active_subscription:
            logger.log_business_event(
                "cancelling_subscription_for_deletion",
                {
                    "user_id": user_id,
                    "subscription_provider": active_subscription.provider.value,
                    "transaction_id": active_subscription.transaction_id,
                },
            )
            subscription_service.cancel_subscription(user_id)

        # Mark user as cancelled (soft delete)
        existing_user.status = UserStatus.CANCELLED
        existing_user.updated_at = datetime.now(timezone.utc)

        success = user_service.update_user(existing_user)
        if success:
            logger.log_business_event(
                "user_marked_as_deleted",
                {
                    "user_id": user_id,
                    "tier": existing_user.tier.value,
                },
            )

            # Queue comprehensive data cleanup job
            cleanup_event = {
                "user_id": user_id,
                "deletion_reason": "cognito_user_deletion",
                "cleanup_steps": [
                    "delete_translations",
                    "delete_usage",
                    "archive_subscriptions",
                    "delete_other_data",
                ],
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }

            # TODO: Send to SQS or invoke cleanup handler directly
            # For now, we'll log that cleanup should be queued
            logger.log_business_event(
                "cleanup_job_queued",
                {
                    "user_id": user_id,
                    "cleanup_event": cleanup_event,
                },
            )
        else:
            logger.log_error(
                ValueError("Failed to mark user as deleted"),
                {"user_id": user_id, "operation": "pre_user_deletion"},
            )

        return event

    except Exception as e:
        logger.log_error(
            e,
            {
                "operation": "pre_user_deletion_handler",
                "user_id": event.userName if hasattr(event, "userName") else "unknown",
            },
        )
        # Don't fail the deletion - return event to allow Cognito deletion to proceed
        return event
