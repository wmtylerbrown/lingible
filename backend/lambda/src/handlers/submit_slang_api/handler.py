"""Lambda handler for slang submission endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.slang import SlangSubmissionResponse
from models.events import SlangSubmissionEvent
from services.slang_submission_service import SlangSubmissionService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import SlangSubmissionEnvelope


# Initialize service at module level (Lambda container reuse)
submission_service = SlangSubmissionService()


@tracer.trace_lambda
@event_parser(model=SlangSubmissionEvent, envelope=SlangSubmissionEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(
    event: SlangSubmissionEvent, context: LambdaContext
) -> SlangSubmissionResponse:
    """Handle slang submission requests from premium users."""

    # Submit slang for review
    response = submission_service.submit_slang(event.request_body, event.user_id)

    return response
