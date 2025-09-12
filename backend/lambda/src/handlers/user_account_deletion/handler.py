"""Lambda handler for user account deletion endpoint."""

from datetime import datetime
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import AccountDeletionEvent
from models.users import AccountDeletionResponse
from services.user_service import UserService
from services.subscription_service import SubscriptionService
from services.translation_service import TranslationService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import AccountDeletionEnvelope
from utils.exceptions import ValidationError
from utils.logging import logger


# Initialize services at module level (Lambda container reuse)
user_service = UserService()
subscription_service = SubscriptionService()
translation_service = TranslationService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=AccountDeletionEvent, envelope=AccountDeletionEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: AccountDeletionEvent, context: LambdaContext) -> AccountDeletionResponse:
    """Handle user account deletion requests from mobile app."""

    # Get user ID from the event (already validated by envelope)
    user_id = event.user_id

    # Validate confirmation text
    if event.confirmation_text != "DELETE":
        raise ValidationError("Confirmation text must be exactly 'DELETE'")

    logger.log_business_event(
        "account_deletion_initiated",
        {
            "user_id": user_id,
            "reason": event.reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Check for active subscription before proceeding
    active_subscription = subscription_service.get_active_subscription(user_id)
    if active_subscription:
        raise ValidationError(
            "Cannot delete account with active subscription. Please cancel your subscription first in the App Store or Google Play Store, then try again.",
            error_code="ACTIVE_SUBSCRIPTION_EXISTS"
        )

    try:
        cleanup_summary = {
            "translations_deleted": 0,
            "data_retention_period": "30 days for billing records"
        }

        # Step 1: Delete all user translations
        translations_deleted = 0
        try:
            translations_deleted = translation_service.delete_user_translations(user_id, is_account_deletion=True)
            logger.log_business_event(
                "translations_deleted_during_account_deletion",
                {"user_id": user_id, "deleted_count": translations_deleted}
            )
        except Exception as e:
            logger.log_error(e, {"operation": "delete_translations_during_deletion", "user_id": user_id})
            # Continue with deletion even if translation deletion fails

        cleanup_summary["translations_deleted"] = translations_deleted

        # Step 2: Delete user account and all associated data
        deletion_success = user_service.delete_user(user_id)

        if not deletion_success:
            raise SystemError(f"Failed to delete user account for user {user_id}")

        # Log successful deletion
        logger.log_business_event(
            "account_deletion_completed",
            {
                "user_id": user_id,
                "translations_deleted": translations_deleted,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Return success response
        return AccountDeletionResponse(
            success=True,
            message="Your account and all associated data have been permanently deleted.",
            deleted_at=datetime.utcnow(),
            cleanup_summary=cleanup_summary
        )

    except Exception as e:
        logger.log_error(
            e,
            {
                "operation": "account_deletion_handler",
                "user_id": user_id,
                "reason": event.reason
            }
        )
        raise
