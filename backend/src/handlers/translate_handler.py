"""Lambda handler for translation endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from ..models.translations import TranslationRequest, TranslationDirection
from ..models.events import TranslationEvent
from ..models.aws import APIGatewayResponse
from ..services.translation_service import TranslationService
from ..utils.logging import logger
from ..utils.tracing import tracer
from ..utils.response import create_success_response
from ..utils.decorators import handle_errors, extract_user_from_parsed_data
from ..utils.envelopes import TranslationEnvelope


# Lambda handler entry point with correct decorator order
@tracer.trace_lambda
@event_parser(model=TranslationEvent, envelope=TranslationEnvelope())
@handle_errors(extract_user_id=extract_user_from_parsed_data)
def handler(event: TranslationEvent, context: LambdaContext) -> APIGatewayResponse:
    """Handle translation requests from mobile app."""

    # Validate user authentication
    if not event.user_id:
        raise ValueError("Valid Cognito token is required for translation requests")

    # Create TranslationRequest
    translation_request = TranslationRequest(
        text=event.request_body.text.strip(),
        direction=TranslationDirection(event.request_body.direction),
        user_id=event.user_id,  # Use the user_id from the event
    )

    # Initialize services
    translation_service = TranslationService()

    # Perform translation
    translation_response = translation_service.translate_text(
        translation_request, event.user_id
    )

    # Log successful translation
    logger.log_business_event(
        "translation_request_completed",
        {
            "user_id": event.user_id,
            "translation_id": translation_response.translation_id,
            "direction": translation_response.direction.value,
            "text_length": len(translation_request.text),
            "processing_time_ms": translation_response.processing_time_ms,
        },
    )

    # Return success response
    return create_success_response(
        "Translation completed successfully",
        {
            "translation_id": translation_response.translation_id,
            "original_text": translation_response.original_text,
            "translated_text": translation_response.translated_text,
            "direction": translation_response.direction.value,
            "confidence_score": translation_response.confidence_score,
            "processing_time_ms": translation_response.processing_time_ms,
            "model_used": translation_response.model_used,
            "created_at": translation_response.created_at.isoformat(),
        },
    )
