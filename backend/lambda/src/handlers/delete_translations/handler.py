"""Lambda handler for deleting all user translations (premium users only)."""

from datetime import datetime
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import SimpleAuthenticatedEvent
from models.base import BaseResponse
from services.translation_service import TranslationService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import SimpleAuthenticatedEnvelope


# Initialize service at module level (Lambda container reuse)
translation_service = TranslationService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=SimpleAuthenticatedEvent, envelope=SimpleAuthenticatedEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: SimpleAuthenticatedEvent, context: LambdaContext) -> BaseResponse:
    """Handle delete all translations requests from mobile app (premium users only)."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Delete all user translations (service handles premium check)
    deleted_count = translation_service.delete_user_translations(user_id)

    # Return success response
    return BaseResponse(
        success=True,
        data={
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} translations",
        },
        timestamp=datetime.now().isoformat(),
    )
