"""Apple webhook handler for subscription updates."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from models.events import WebhookEvent
from models.subscriptions import WebhookResponse
from models.users import UserTier
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from utils.decorators import api_handler
from utils.tracing import tracer

# Initialize services at module level for Lambda container reuse
subscription_service = SubscriptionService()
user_service = UserService()


@event_parser(model=WebhookEvent)
@api_handler()
@tracer.trace_method("apple_webhook_handler")
def handler(
    event: WebhookEvent, context: LambdaContext
) -> WebhookResponse:
    """Handle Apple subscription webhook."""
    # Extract webhook data from validated request body
    notification_type = event.request_body.notification_type
    transaction_id = event.request_body.transaction_id

    success = False

    # Handle different webhook types with focused methods
    if notification_type == "RENEWAL":
        success = subscription_service.handle_renewal_webhook(transaction_id)

    elif notification_type == "CANCEL":
        # Step 1: Cancel subscription
        subscription_cancelled = subscription_service.handle_cancellation_webhook(transaction_id)

        # Step 2: Downgrade user tier
        if subscription_cancelled:
            # Find user ID for downgrade
            user_id = subscription_service.find_user_id_by_transaction_id(transaction_id)
            if user_id:
                user_downgraded = user_service.downgrade_user_tier(user_id, UserTier.FREE)
                success = subscription_cancelled and user_downgraded
            else:
                success = subscription_cancelled  # Subscription cancelled but no user found
        else:
            success = False

    elif notification_type == "FAILED_PAYMENT":
        # Step 1: Mark subscription as expired
        subscription_expired = subscription_service.handle_failed_payment_webhook(transaction_id)

        # Step 2: Downgrade user tier
        if subscription_expired:
            # Find user ID for downgrade
            user_id = subscription_service.find_user_id_by_transaction_id(transaction_id)
            if user_id:
                user_downgraded = user_service.downgrade_user_tier(user_id, UserTier.FREE)
                success = subscription_expired and user_downgraded
            else:
                success = subscription_expired  # Subscription expired but no user found
        else:
            success = False

    else:
        # Unknown webhook type - log and return success
        success = True

    return WebhookResponse(
        success=success,
        message=(
            "Webhook processed successfully" if success else "Webhook processing failed"
        ),
    )
