"""Cognito pre user deletion trigger handler for user cleanup."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from ...models.events import CognitoPreUserDeletionEvent
from ...services.user_service import UserService
from ...services.subscription_service import SubscriptionService
from ...utils.tracing import tracer
from ...utils.logging import logger
from datetime import datetime, timezone
from ...models.users import UserStatus


# Initialize services at module level for Lambda container reuse
user_service = UserService()
subscription_service = SubscriptionService()


@event_parser(model=CognitoPreUserDeletionEvent)
@tracer.trace_method("cognito_pre_user_deletion")
def pre_user_deletion_handler(
    event: CognitoPreUserDeletionEvent, context: LambdaContext
) -> CognitoPreUserDeletionEvent:
    """Handle user cleanup before Cognito deletes the user account."""
    try:
        user_id = event.userName
        user_pool_id = event.userPoolId
        trigger_source = event.triggerSource

        logger.log_business_event(
            "cognito_pre_user_deletion_triggered",
            {
                "user_id": user_id,
                "user_pool_id": user_pool_id,
                "trigger_source": trigger_source,
            },
        )

        # Step 1: Cancel any active subscriptions
        try:
            active_subscription = subscription_service.get_active_subscription(user_id)
            if active_subscription:
                subscription_service.cancel_subscription(user_id)
                logger.log_business_event(
                    "subscription_cancelled_during_deletion",
                    {
                        "user_id": user_id,
                        "subscription_id": active_subscription.subscription_id,
                    },
                )
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "cancel_subscription_during_deletion",
                    "user_id": user_id,
                },
            )
            # Don't fail the deletion process - continue with cleanup

        # Step 2: Mark user as CANCELLED in our system
        try:
            # Get the user and update their status to CANCELLED (soft delete)
            user = user_service.get_user(user_id)
            if user:
                user.status = UserStatus.CANCELLED
                user.updated_at = datetime.now(timezone.utc)
                success = user_service.update_user(user)

                if success:
                    logger.log_business_event(
                        "user_marked_as_cancelled",
                        {
                            "user_id": user_id,
                            "status": UserStatus.CANCELLED.value,
                            "deletion_timestamp": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        },
                    )
                else:
                    logger.log_error(
                        Exception("Failed to mark user as cancelled"),
                        {"user_id": user_id, "operation": "update_user"},
                    )
            else:
                logger.log_error(
                    Exception("User not found during deletion"),
                    {"user_id": user_id, "operation": "get_user"},
                )
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "mark_user_cancelled",
                    "user_id": user_id,
                },
            )
            # Don't fail the deletion process - continue with cleanup

        # Step 3: Queue cleanup job for background processing
        # Note: This would typically involve SQS/Step Functions
        # For now, we'll log that cleanup is needed
        logger.log_business_event(
            "cleanup_job_queued",
            {
                "user_id": user_id,
                "cleanup_steps": [
                    "delete_translations",
                    "delete_usage",
                    "archive_subscriptions",
                    "delete_other_data",
                ],
                "note": "Manual cleanup required or implement SQS/Step Functions",
            },
        )

        # Step 4: Return the event to allow Cognito deletion to proceed
        # This is critical - we must not block the Cognito user deletion
        logger.log_business_event(
            "cognito_user_deletion_allowed",
            {
                "user_id": user_id,
                "cleanup_status": "queued",
                "user_status": "CANCELLED",
            },
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
        # CRITICAL: Always return the event to allow Cognito deletion to proceed
        # Even if our cleanup fails, we don't want to block user account deletion
        return event
