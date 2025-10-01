"""Lambda handler for deleting a specific translation (premium users only)."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from datetime import datetime
from models.events import PathParameterEvent
from models.base import BaseResponse
from services.translation_service import TranslationService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import PathParameterEnvelope


# Initialize service at module level (Lambda container reuse)
translation_service = TranslationService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=PathParameterEvent, envelope=PathParameterEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: PathParameterEvent, context: LambdaContext) -> BaseResponse:
    """Handle translation deletion requests from mobile app (premium users only)."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Extract translation ID from path parameters (guaranteed by envelope)
    translation_id = event.path_parameters.get("translation_id")
    if not translation_id:
        raise ValueError("Translation ID is required")

    # Delete the translation (service handles premium check)
    success = translation_service.delete_translation(user_id, translation_id)

    if not success:
        raise Exception("Failed to delete translation")

    # Return success response
    return BaseResponse(
        success=True,
        data={
            "translation_id": translation_id,
            "message": "Translation deleted successfully",
        },
        timestamp=datetime.now(),
    )
