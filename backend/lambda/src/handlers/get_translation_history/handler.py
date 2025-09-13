"""Lambda handler for getting translation history (premium users only)."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import TranslationHistoryEvent
from models.translations import TranslationHistoryServiceResult
from services.translation_service import TranslationService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import TranslationHistoryEnvelope


# Initialize service at module level (Lambda container reuse)
translation_service = TranslationService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=TranslationHistoryEvent, envelope=TranslationHistoryEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(
    event: TranslationHistoryEvent, context: LambdaContext
) -> TranslationHistoryServiceResult:
    """Handle translation history requests from mobile app (premium users only)."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Get query parameters from the envelope
    limit = getattr(event, "limit", 20) or 20
    last_evaluated_key = getattr(event, "last_evaluated_key", None)

    # Get translation history (service handles premium check)
    result = translation_service.get_translation_history(
        user_id=user_id,
        limit=limit,
        last_evaluated_key=last_evaluated_key,
    )

    # Return the service result directly - decorator handles the API response creation
    return result
