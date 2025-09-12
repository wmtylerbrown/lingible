"""Apple webhook handler for subscription updates."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from models.events import WebhookEvent
from models.subscriptions import WebhookResponse
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
    receipt_data = event.request_body.receipt_data

    # Process webhook
    success = subscription_service.handle_apple_webhook(
        notification_type, transaction_id, receipt_data
    )

    # Note: User tier downgrades are now handled by the SubscriptionService
    # No need for additional handling here since the service manages the full flow

    return WebhookResponse(
        success=success,
        message=(
            "Webhook processed successfully" if success else "Webhook processing failed"
        ),
    )
