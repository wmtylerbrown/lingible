"""Lambda handler for async slang validation processing."""

import json
from typing import Any, Dict

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import SlangValidationEvent
from models.slang import ApprovalType
from services.slang_validation_service import SlangValidationService
from services.slang_submission_service import SlangSubmissionService
from repositories.submissions_repository import SubmissionsRepository
from utils.smart_logger import logger
from utils.tracing import tracer


@tracer.trace_lambda
@event_parser(model=SlangValidationEvent)
def handler(event: SlangValidationEvent, context: LambdaContext) -> Dict[str, Any]:
    """Process async slang validation requests from SNS."""
    logger.log_business_event(
        "validation_request_processing",
        {
            "submission_id": event.submission_id,
            "user_id": event.user_id,
            "slang_term": event.slang_term,
        },
    )

    # Initialize services
    validation_service = SlangValidationService()
    submission_service = SlangSubmissionService()
    repository = SubmissionsRepository()

    # Get submission from repository
    submission = repository.get_submission_by_id(event.submission_id)
    if not submission:
        logger.log_error(
            Exception("Submission not found"),
            {"operation": "get_submission", "submission_id": event.submission_id},
        )
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Submission not found"}),
        }

    try:

        # Validate the submission
        logger.log_business_event(
            "validation_started", {"submission_id": event.submission_id}
        )

        validation_result = validation_service.validate_submission(submission)

        # Update submission with validation result
        repository.update_validation_result(
            event.submission_id, event.user_id, validation_result
        )

        # Determine status based on validation
        validation_status = validation_service.determine_status(validation_result)

        # Check if should auto-approve
        if validation_service.should_auto_approve(validation_result):
            logger.log_business_event(
                "submission_auto_approved",
                {
                    "submission_id": event.submission_id,
                    "confidence": str(validation_result.confidence),
                    "usage_score": validation_result.usage_score,
                },
            )

            # Auto-approve the submission
            repository.update_approval_status(
                event.submission_id,
                event.user_id,
                validation_status,
                ApprovalType.LLM_AUTO,
            )

            # Notify admins of auto-approval
            submission_service._publish_auto_approval_notification(
                submission, validation_result
            )

            # Increment user's approved count
            submission_service.user_service.increment_slang_approved(event.user_id)

            logger.log_business_event(
                "submission_auto_approved_complete",
                {"submission_id": event.submission_id, "user_id": event.user_id},
            )
        else:
            logger.log_business_event(
                "submission_requires_review",
                {
                    "submission_id": event.submission_id,
                    "confidence": str(validation_result.confidence),
                    "usage_score": validation_result.usage_score,
                },
            )

            # Update status to validated (ready for community voting or admin review)
            repository.update_validation_result(
                event.submission_id, event.user_id, validation_result
            )

            # Notify admins of submission requiring review
            submission_service._publish_submission_notification(submission)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Validation completed",
                    "submission_id": event.submission_id,
                    "auto_approved": validation_service.should_auto_approve(
                        validation_result
                    ),
                }
            ),
        }

    except Exception as e:
        logger.log_error(
            e,
            {"operation": "process_validation", "submission_id": event.submission_id},
        )

        # Update submission with error status
        try:
            repository.update_validation_result(
                event.submission_id,
                event.user_id,
                validation_service._fallback_validation(submission),
            )
        except Exception as update_error:
            logger.log_error(
                update_error,
                {
                    "operation": "update_submission_error_status",
                    "submission_id": event.submission_id,
                },
            )

        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "Internal server error", "submission_id": event.submission_id}
            ),
        }
