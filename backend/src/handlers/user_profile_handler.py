"""Lambda handler for user profile endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.events import UserProfileEvent
from ..models.users import UserResponse
from ..services.user_service import UserService
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.decorators import api_handler, extract_user_from_parsed_data
from ..utils.envelopes import UserProfileEnvelope
from ..utils.exceptions import ResourceNotFoundError


# Initialize services at module level (Lambda container reuse)
user_service = UserService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=UserProfileEvent, envelope=UserProfileEnvelope())
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: UserProfileEvent, context: LambdaContext) -> UserResponse:
    """Handle user profile requests from mobile app."""

    # Get user ID from the event (already validated by envelope)
    user_id = event.user_id

    # Get user profile (static, cacheable data)
    user = user_service.get_user(user_id)
    if not user:
        raise ResourceNotFoundError("user", user_id or "unknown")

    # Log successful profile retrieval
    logger.log_business_event(
        "user_profile_retrieved",
        {
            "user_id": user_id,
            "tier": user.tier,
            "status": user.status,
        },
    )

    # Return the response model - decorator handles the API response creation
    return user.to_api_response()
