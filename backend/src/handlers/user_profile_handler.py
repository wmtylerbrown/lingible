"""Lambda handler for user profile endpoint."""

from typing import Dict, Any

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.aws import APIGatewayResponse
from ..services.user_service import UserService
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.response import create_model_response
from ..utils.decorators import handle_errors, extract_user_from_parsed_data
from ..utils.envelopes import APIGatewayEnvelope


class UserProfileEnvelope(APIGatewayEnvelope):
    """Envelope for user profile endpoints that extracts user info."""

    def _parse_api_gateway(
        self, event: Any, model: type, base_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse user profile specific data."""
        # For GET requests, we don't need to parse a request body
        # Just return the base data with user info
        return base_data


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=Dict[str, Any], envelope=UserProfileEnvelope())
@handle_errors(extract_user_id=extract_user_from_parsed_data)
def handler(event: Dict[str, Any], context: LambdaContext) -> APIGatewayResponse:
    """Handle user profile requests from mobile app."""

    # Extract user info from the event
    user_id = event.get("user_id")
    if not user_id:
        raise ValueError("Valid Cognito token is required for profile requests")

    # Initialize services
    user_service = UserService()

    # Get user profile (static, cacheable data)
    user = user_service.get_user(user_id)
    if not user:
        raise ValueError(f"User not found: {user_id}")

    # Log successful profile retrieval
    logger.log_business_event(
        "user_profile_retrieved",
        {
            "user_id": user_id,
            "tier": user.tier,
            "status": user.status,
        },
    )

    # Return success response with profile data
    return create_model_response(
        "User profile retrieved successfully",
        user.to_api_response(),
    )
