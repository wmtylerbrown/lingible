"""Lambda handler for quiz submission endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import QuizSubmissionEvent
from models.quiz import QuizResult
from services.quiz_service import QuizService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import QuizSubmissionEnvelope
from utils.smart_logger import logger


# Initialize service at module level (Lambda container reuse)
quiz_service = QuizService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=QuizSubmissionEvent, envelope=QuizSubmissionEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: QuizSubmissionEvent, context: LambdaContext) -> QuizResult:
    """Handle quiz submission requests from mobile app."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Get submission from the parsed request body
    submission = event.request_body

    # Debug logging for development
    logger.log_debug(
        "Quiz submission request started",
        {
            "user_id": user_id,
            "challenge_id": submission.challenge_id,
            "answer_count": len(submission.answers),
            "event_type": "quiz_submission_request",
        },
    )

    # Submit the quiz and get results
    result = quiz_service.submit_quiz(user_id, submission)

    # Debug logging for successful response
    logger.log_debug(
        "Quiz submission processed successfully",
        {
            "user_id": user_id,
            "challenge_id": submission.challenge_id,
            "score": result.score,
            "total_questions": result.total_questions,
            "event_type": "quiz_submission_success",
        },
    )

    # Return the result directly - decorator handles the API response creation
    return result
