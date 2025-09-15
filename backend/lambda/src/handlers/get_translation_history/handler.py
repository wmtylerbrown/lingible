"""Lambda handler for getting translation history (premium users only)."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import TranslationHistoryEvent
from models.translations import TranslationHistoryServiceResult
from services.translation_service import TranslationService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import TranslationHistoryEnvelope
from utils.logging import logger


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
    offset = getattr(event, "offset", 0) or 0
    last_evaluated_key = getattr(event, "last_evaluated_key", None)

    # Debug logging for development
    logger.log_debug(
        "Translation history request started",
        {
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
            "last_evaluated_key": last_evaluated_key,
            "event_type": "translation_history_request"
        }
    )

    # For offset-based pagination, we need to fetch more items and slice
    # This is not efficient for large offsets, but works for the current use case
    if offset > 0 and last_evaluated_key is None:
        # Fetch more items to account for offset
        fetch_limit = limit + offset
        result = translation_service.get_translation_history(
            user_id=user_id,
            limit=fetch_limit,
            last_evaluated_key=last_evaluated_key,
        )

        # Slice the results to apply offset
        if len(result.translations) > offset:
            result.translations = result.translations[offset:]
            # Adjust has_more based on whether we have more items after slicing
            result.has_more = len(result.translations) == limit
        else:
            result.translations = []
            result.has_more = False
    else:
        # Use normal pagination for first page or when using last_evaluated_key
        result = translation_service.get_translation_history(
            user_id=user_id,
            limit=limit,
            last_evaluated_key=last_evaluated_key,
        )

    # Debug logging for successful response
    logger.log_debug(
        "Translation history retrieved successfully",
        {
            "user_id": user_id,
            "result_count": len(result.translations),
            "total_count": result.total_count,
            "has_more": result.has_more,
            "event_type": "translation_history_success"
        }
    )

    # Return the service result directly - decorator handles the API response creation
    return result
