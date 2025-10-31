"""Lambda handler for quiz history endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import QuizHistoryEvent
from models.quiz import QuizHistory
from services.quiz_service import QuizService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import QuizHistoryEnvelope
from utils.smart_logger import logger


# Initialize service at module level (Lambda container reuse)
quiz_service = QuizService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=QuizHistoryEvent, envelope=QuizHistoryEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: QuizHistoryEvent, context: LambdaContext) -> QuizHistory:
    """Handle quiz history requests from mobile app."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Debug logging for development
    logger.log_debug(
        "Quiz history request started",
        {
            "user_id": user_id,
            "event_type": "quiz_history_request",
        },
    )

    # Get quiz history and eligibility
    history = quiz_service.check_quiz_eligibility(user_id)

    # Debug logging for successful response
    logger.log_debug(
        "Quiz history retrieved successfully",
        {
            "user_id": user_id,
            "can_take_quiz": history.can_take_quiz,
            "total_quizzes": history.total_quizzes,
            "average_score": history.average_score,
            "event_type": "quiz_history_success",
        },
    )

    # Return the history directly - decorator handles the API response creation
    return history
