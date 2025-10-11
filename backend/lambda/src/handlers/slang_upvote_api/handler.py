"""Lambda handler for upvoting slang submissions."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.slang import UpvoteResponse
from models.events import PathParameterEvent
from services.slang_submission_service import SlangSubmissionService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import PathParameterEnvelope


# Initialize service at module level (Lambda container reuse)
submission_service = SlangSubmissionService()


@tracer.trace_lambda
@event_parser(model=PathParameterEvent, envelope=PathParameterEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: PathParameterEvent, context: LambdaContext) -> UpvoteResponse:
    """Handle upvote requests for slang submissions."""

    # Get user ID from event (voter)
    voter_user_id = event.user_id

    # Extract submission ID from path parameters
    submission_id = event.path_parameters.get("submission_id")
    if not submission_id:
        raise ValueError("Submission ID is required")

    # Upvote the submission
    response = submission_service.upvote_submission(submission_id, voter_user_id)

    return response
