"""Lambda handler for user usage statistics endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.events import UserUsageEvent
from ..models.users import UserUsageResponse
from ..services.user_service import UserService
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.decorators import handle_errors, extract_user_from_parsed_data
from ..utils.envelopes import UserUsageEnvelope


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=UserUsageEvent, envelope=UserUsageEnvelope())
@handle_errors(extract_user_id=extract_user_from_parsed_data)
def handler(event: UserUsageEvent, context: LambdaContext) -> UserUsageResponse:
    """Handle user usage statistics requests from mobile app."""

    # Extract user info from the event
    user_id = event.user_id
    if not user_id:
        raise ValueError("Valid Cognito token is required for usage requests")

    # Initialize services
    user_service = UserService()

    # Get user usage statistics (dynamic data)
    user_usage = user_service.get_user_usage(user_id)

    # Log successful usage retrieval
    logger.log_business_event(
        "user_usage_retrieved",
        {
            "user_id": user_id,
            "tier": user_usage.tier,
            "daily_used": user_usage.daily_used,
            "daily_remaining": user_usage.daily_remaining,
        },
    )

    # Return the response model - decorator handles the API response creation
    return user_usage
