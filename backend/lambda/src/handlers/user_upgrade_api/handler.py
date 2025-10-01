"""User upgrade handler for subscription management."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from utils.envelopes import UserUpgradeEnvelope
from models.events import UserUpgradeEvent
from models.users import UpgradeResponse, UserTier
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.tracing import tracer
from utils.exceptions import ValidationError

# Initialize services at module level for Lambda container reuse
subscription_service = SubscriptionService()
user_service = UserService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=UserUpgradeEvent, envelope=UserUpgradeEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: UserUpgradeEvent, context: LambdaContext) -> UpgradeResponse:
    """Upgrade user subscription after validating purchase."""
    # Extract upgrade data from validated request body
    user_id = event.user_id

    # Step 1: Validate user exists
    user = user_service.get_user(user_id)
    if not user:
        raise ValidationError("User not found", error_code="USER_NOT_FOUND")

    # Step 2: Create subscription via subscription service
    transaction_data = event.request_body.to_transaction_data()
    subscription_service.validate_and_create_subscription(
        user_id=user_id, transaction_data=transaction_data
    )

    # Step 3: Upgrade user tier via user service
    user_service.upgrade_user_tier(user_id, UserTier.PREMIUM)

    # Get subscription expiration date from the transaction data
    expires_at = transaction_data.expiration_date

    # Return upgrade response
    return UpgradeResponse(
        success=True,
        message="User successfully upgraded to premium",
        tier="premium",
        expires_at=expires_at,
    )
