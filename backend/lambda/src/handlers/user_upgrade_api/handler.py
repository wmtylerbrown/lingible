"""User upgrade handler for subscription management."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from utils.envelopes import UserUpgradeEnvelope
from models.events import UserUpgradeEvent
from models.users import UserResponse, UserTier
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.tracing import tracer
from utils.exceptions import ValidationError, SystemError

# Initialize services at module level for Lambda container reuse
subscription_service = SubscriptionService()
user_service = UserService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=UserUpgradeEvent, envelope=UserUpgradeEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: UserUpgradeEvent, context: LambdaContext) -> UserResponse:
    """Upgrade user subscription after validating purchase."""
    # Extract upgrade data from validated request body
    provider = event.request_body.provider
    receipt_data = event.request_body.receipt_data
    transaction_id = event.request_body.transaction_id
    user_id = event.user_id

    # Step 1: Validate user exists
    user = user_service.get_user(user_id)
    if not user:
        raise ValidationError("User not found", error_code="USER_NOT_FOUND")

    # Step 2: Create subscription via subscription service
    subscription_created = subscription_service.validate_and_create_subscription(
        user_id=user_id,
        provider=provider,
        receipt_data=receipt_data,
        transaction_id=transaction_id
    )
    if not subscription_created:
        raise SystemError("Failed to create subscription")

    # Step 3: Upgrade user tier via user service
    tier_updated = user_service.upgrade_user_tier(user_id, UserTier.PREMIUM)
    if not tier_updated:
        raise SystemError("Failed to upgrade user tier")

    # Return updated user
    updated_user = user_service.get_user(user_id)
    if not updated_user:
        raise SystemError("User not found after tier update")

    return updated_user.to_api_response()
