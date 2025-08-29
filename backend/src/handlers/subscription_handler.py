"""Subscription handler for managing user subscriptions."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from ..models.subscriptions import (
    SubscriptionResponse,
    SubscriptionListResponse,
    SubscriptionHistoryListResponse,
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
)
from ..models.events import SubscriptionEvent
from ..services.subscription_service import SubscriptionService
from ..utils.decorators import api_handler

# Initialize service at module level for Lambda container reuse
subscription_service = SubscriptionService()


@event_parser(model=SubscriptionEvent)
@api_handler()
def get_subscriptions(
    event: SubscriptionEvent, context: LambdaContext
) -> SubscriptionListResponse:
    """Get all subscriptions for the authenticated user."""
    subscriptions = subscription_service.get_user_subscriptions(event.user_id)

    # Convert to API response models
    subscription_responses = [sub.to_api_response() for sub in subscriptions]

    return SubscriptionListResponse(
        subscriptions=subscription_responses, total_count=len(subscription_responses)
    )


@event_parser(model=SubscriptionEvent)
@api_handler()
def get_active_subscription(
    event: SubscriptionEvent, context: LambdaContext
) -> SubscriptionResponse:
    """Get the active subscription for the authenticated user."""
    subscription = subscription_service.get_active_subscription(event.user_id)

    if not subscription:
        # Return a default free subscription response
        return SubscriptionResponse(
            subscription_id="",
            provider="none",
            tier="free",
            status="active",
            start_date="",
            end_date=None,
            created_at="",
        )

    return subscription.to_api_response()


@event_parser(model=SubscriptionEvent)
@api_handler()
def get_subscription_history(
    event: SubscriptionEvent, context: LambdaContext
) -> SubscriptionHistoryListResponse:
    """Get subscription history for the authenticated user."""
    # Get limit from query parameters (default to 10)
    limit = 10
    if event.event.get("queryStringParameters"):
        limit_param = event.event["queryStringParameters"].get("limit")
        if limit_param:
            try:
                limit = int(limit_param)
                limit = max(1, min(limit, 50))  # Clamp between 1 and 50
            except ValueError:
                limit = 10

    history = subscription_service.get_subscription_history(event.user_id, limit)

    # Convert to API response models
    history_responses = [h.to_api_response() for h in history]

    return SubscriptionHistoryListResponse(
        history=history_responses, total_count=len(history_responses)
    )


@event_parser(model=SubscriptionEvent)
@api_handler()
def create_subscription(
    event: SubscriptionEvent, context: LambdaContext
) -> SubscriptionResponse:
    """Create a new subscription for the authenticated user."""
    # Parse request body
    body = event.event.get("body", "{}")
    if isinstance(body, str):
        import json

        body = json.loads(body)

    request = CreateSubscriptionRequest(**body)

    subscription = subscription_service.create_subscription(event.user_id, request)
    return subscription.to_api_response()


@event_parser(model=SubscriptionEvent)
@api_handler()
def update_subscription(
    event: SubscriptionEvent, context: LambdaContext
) -> SubscriptionResponse:
    """Update an existing subscription."""
    # Get subscription ID from path parameters
    subscription_id = event.event.get("pathParameters", {}).get("subscription_id")
    if not subscription_id:
        raise ValueError("Subscription ID is required")

    # Parse request body
    body = event.event.get("body", "{}")
    if isinstance(body, str):
        import json

        body = json.loads(body)

    request = UpdateSubscriptionRequest(**body)

    subscription = subscription_service.update_subscription(
        event.user_id, subscription_id, request
    )
    return subscription.to_api_response()


@event_parser(model=SubscriptionEvent)
@api_handler()
def cancel_subscription(
    event: SubscriptionEvent, context: LambdaContext
) -> SubscriptionResponse:
    """Cancel a subscription."""
    # Get subscription ID from path parameters
    subscription_id = event.event.get("pathParameters", {}).get("subscription_id")
    if not subscription_id:
        raise ValueError("Subscription ID is required")

    subscription = subscription_service.cancel_subscription(
        event.user_id, subscription_id
    )
    return subscription.to_api_response()
