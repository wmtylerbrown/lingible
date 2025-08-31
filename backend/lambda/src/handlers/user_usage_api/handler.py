"""Lambda handler for user usage statistics endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import UserUsageEvent
from models.users import UserUsageResponse
from services.user_service import UserService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import SimpleAuthenticatedEnvelope


# Initialize services at module level (Lambda container reuse)
user_service = UserService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=UserUsageEvent, envelope=SimpleAuthenticatedEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: UserUsageEvent, context: LambdaContext) -> UserUsageResponse:
    """Handle user usage statistics requests from mobile app."""

    # Get user ID from the event (already validated by envelope)
    user_id = event.user_id

    # Get user usage statistics (dynamic data)
    user_usage = user_service.get_user_usage(user_id)

    # Return the response model - decorator handles the API response creation
    return user_usage
