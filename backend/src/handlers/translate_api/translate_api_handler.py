"""Lambda handler for translation endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.translations import (
    TranslationRequestInternal,
    TranslationDirection,
    TranslationResponse,
)
from ..models.events import TranslationEvent
from ..services.translation_service import TranslationService
from ..utils.tracing import tracer
from ..utils.decorators import api_handler, extract_user_from_parsed_data
from ..utils.envelopes import TranslationEnvelope


# Initialize services at module level (Lambda container reuse)
translation_service = TranslationService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=TranslationEvent, envelope=TranslationEnvelope())
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: TranslationEvent, context: LambdaContext) -> TranslationResponse:
    """Handle translation requests from mobile app."""

    # Create TranslationRequest
    translation_request = TranslationRequestInternal(
        text=event.request_body.text.strip(),
        direction=TranslationDirection(event.request_body.direction),
        user_id=event.user_id,  # Use the user_id from the event
    )

    # Perform translation
    translation = translation_service.translate_text(translation_request, event.user_id)

    # Return the response model - decorator handles the API response creation
    return translation.to_api_response()
