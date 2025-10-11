"""Lambda handler for admin approval of slang submissions."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.slang import AdminApprovalResponse
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
def handler(event: PathParameterEvent, context: LambdaContext) -> AdminApprovalResponse:
    """Handle admin approval of slang submissions (admin only)."""

    # Get admin user ID from event
    admin_user_id = event.user_id

    # Extract submission ID from path parameters
    submission_id = event.path_parameters.get("submission_id")
    if not submission_id:
        raise ValueError("Submission ID is required")

    # TODO: Add admin tier check here (require UserTier.ADMIN)
    # For now, any authenticated user can approve (will add proper auth in CDK)

    # Approve the submission
    response = submission_service.admin_approve(submission_id, admin_user_id)

    return response
