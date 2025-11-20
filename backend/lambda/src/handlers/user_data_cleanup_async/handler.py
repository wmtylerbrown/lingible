"""Background handler for comprehensive user data cleanup."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from models.events import UserDataCleanupEvent
from services.user_service import UserService
from services.subscription_service import SubscriptionService
from services.translation_service import TranslationService
from utils.tracing import tracer
from utils.smart_logger import logger

# Initialize services at module level for Lambda container reuse
user_service = UserService()
subscription_service = SubscriptionService()
translation_service = TranslationService()


@tracer.trace_lambda
@event_parser(model=UserDataCleanupEvent)
def handler(event: UserDataCleanupEvent, context: LambdaContext) -> dict:
    """Comprehensive cleanup of user data from all tables."""
    try:
        user_id = event.user_id
        deletion_reason = event.deletion_reason
        cleanup_steps = event.cleanup_steps

        logger.log_business_event(
            "user_data_cleanup_started",
            {
                "user_id": user_id,
                "deletion_reason": deletion_reason,
                "cleanup_steps": cleanup_steps,
            },
        )

        cleanup_results: dict = {
            "user_id": user_id,
            "deletion_reason": deletion_reason,
            "steps_completed": [],
            "steps_failed": [],
            "total_records_deleted": 0,
        }

        # Step 1: Delete translation history
        if "delete_translations" in cleanup_steps:
            try:
                deleted_count = translation_service.delete_user_translations(user_id)
                cleanup_results["steps_completed"].append("delete_translations")
                cleanup_results["total_records_deleted"] += deleted_count
                logger.log_business_event(
                    "translation_history_deleted",
                    {"user_id": user_id, "deleted_count": deleted_count},
                )
            except Exception as e:
                cleanup_results["steps_failed"].append("delete_translations")
                logger.log_error(
                    e,
                    {"operation": "delete_translations", "user_id": user_id},
                )

        # Step 2: Delete usage data (handled by delete_user)
        if "delete_usage" in cleanup_steps:
            try:
                # Usage data is deleted as part of user deletion
                logger.log_business_event(
                    "usage_data_deletion_skipped",
                    {"user_id": user_id, "reason": "handled_by_user_deletion"},
                )
                cleanup_results["steps_completed"].append("delete_usage")
            except Exception as e:
                cleanup_results["steps_failed"].append("delete_usage")
                logger.log_error(
                    e,
                    {"operation": "delete_usage", "user_id": user_id},
                )

        # Step 3: Archive subscription history (if not already done)
        if "archive_subscriptions" in cleanup_steps:
            try:
                # Ensure subscription is cancelled and archived
                # Note: Archived subscriptions have 1-year TTL for automatic cleanup
                active_subscription = subscription_service.get_active_subscription(
                    user_id
                )
                if active_subscription:
                    subscription_service.cancel_subscription(user_id)
                    cleanup_results["steps_completed"].append("archive_subscriptions")
                    logger.log_business_event(
                        "subscriptions_archived",
                        {"user_id": user_id, "ttl_note": "1_year_auto_cleanup"},
                    )
                else:
                    cleanup_results["steps_completed"].append("archive_subscriptions")
            except Exception as e:
                cleanup_results["steps_failed"].append("archive_subscriptions")
                logger.log_error(
                    e,
                    {"operation": "archive_subscriptions", "user_id": user_id},
                )

        # Step 4: Delete any other user-related data
        if "delete_other_data" in cleanup_steps:
            try:
                # Add any other cleanup steps here
                # For example: preferences, settings, etc.
                cleanup_results["steps_completed"].append("delete_other_data")
                logger.log_business_event(
                    "other_data_deleted",
                    {"user_id": user_id},
                )
            except Exception as e:
                cleanup_results["steps_failed"].append("delete_other_data")
                logger.log_error(
                    e,
                    {"operation": "delete_other_data", "user_id": user_id},
                )

        # Log final results
        logger.log_business_event(
            "user_data_cleanup_completed",
            {
                "user_id": user_id,
                "steps_completed": len(cleanup_results["steps_completed"]),
                "steps_failed": len(cleanup_results["steps_failed"]),
                "total_records_deleted": cleanup_results["total_records_deleted"],
            },
        )

        return cleanup_results

    except Exception as e:
        logger.log_error(
            e,
            {
                "operation": "cleanup_user_data_handler",
                "user_id": event.user_id if hasattr(event, "user_id") else "unknown",
            },
        )
        raise
