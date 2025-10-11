"""Lambda handler for retrieving pending slang submissions for community voting."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.slang import PendingSubmissionsResponse
from models.events import PendingSubmissionsEvent
from services.slang_submission_service import SlangSubmissionService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import PendingSubmissionsEnvelope


# Initialize service at module level (Lambda container reuse)
submission_service = SlangSubmissionService()


@tracer.trace_lambda
@event_parser(model=PendingSubmissionsEvent, envelope=PendingSubmissionsEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(
    event: PendingSubmissionsEvent, context: LambdaContext
) -> PendingSubmissionsResponse:
    """Handle requests to get pending slang submissions available for voting."""

    # Get limit from event (envelope extracts from query parameters)
    limit = event.limit or 50

    # Get pending submissions (VALIDATED status - ready for community voting)
    response = submission_service.get_pending_submissions(limit)

    return response
