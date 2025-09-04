"""User upgrade handler for subscription management."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from utils.envelopes import UserUpgradeEnvelope
from models.events import UserUpgradeEvent
from models.users import UserResponse
from services.subscription_service import SubscriptionService
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.tracing import tracer

# Initialize service at module level for Lambda container reuse
subscription_service = SubscriptionService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=UserUpgradeEvent, envelope=UserUpgradeEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def upgrade_user(event: UserUpgradeEvent, context: LambdaContext) -> UserResponse:
    """Upgrade user subscription after validating purchase."""
    # Extract upgrade data from validated request body
    provider = event.request_body.provider
    receipt_data = event.request_body.receipt_data
    transaction_id = event.request_body.transaction_id

    # Upgrade user
    user = subscription_service.upgrade_user(
        event.user_id, provider, receipt_data, transaction_id
    )

    return user.to_api_response()
