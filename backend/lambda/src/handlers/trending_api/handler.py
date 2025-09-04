"""Lambda handler for trending terms endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import TrendingEvent
from models.trending import TrendingListResponse, TrendingCategory
from services.trending_service import TrendingService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import SimpleAuthenticatedEnvelope
from utils.exceptions import ValidationError


# Initialize services at module level (Lambda container reuse)
trending_service = TrendingService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=TrendingEvent, envelope=SimpleAuthenticatedEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: TrendingEvent, context: LambdaContext) -> TrendingListResponse:
    """Handle trending terms requests from mobile app."""

    # Get user ID from the event (already validated by envelope)
    user_id = event.user_id

    # Parse and validate query parameters
    limit = event.limit or 50
    category = None
    active_only = event.active_only if event.active_only is not None else True

    # Parse category if provided
    if event.category:
        try:
            category = TrendingCategory(event.category.lower())
        except ValueError:
            raise ValidationError(f"Invalid category: {event.category}. Valid categories are: {[c.value for c in TrendingCategory]}")

    # Get trending terms from service - service will handle user lookup and tier logic
    trending_response = trending_service.get_trending_terms(
        user_id=user_id,
        limit=limit,
        category=category,
        active_only=active_only,
    )

    # Return the response model - decorator handles the API response creation
    return trending_response
