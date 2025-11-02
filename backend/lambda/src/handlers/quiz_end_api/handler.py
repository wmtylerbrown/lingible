"""Lambda handler for quiz end endpoint (stateless per-question API)."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import QuizEndEvent
from models.quiz import QuizResult
from services.quiz_service import QuizService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import QuizEndEnvelope
from utils.smart_logger import logger


# Initialize service at module level (Lambda container reuse)
quiz_service = QuizService()


# Stateless quiz end endpoint (new API)
@tracer.trace_lambda
@event_parser(model=QuizEndEvent, envelope=QuizEndEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: QuizEndEvent, context: LambdaContext) -> QuizResult:
    """Handle POST /quiz/end - end quiz session and get final results (stateless API)."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Get end request from the parsed request body
    end_request = event.request_body

    logger.log_debug(
        "Quiz end request",
        {
            "user_id": user_id,
            "session_id": end_request.session_id,
            "event_type": "quiz_end_request",
        },
    )

    # End the session and get final results
    result = quiz_service.end_session(user_id, end_request.session_id)

    logger.log_debug(
        "Quiz session ended",
        {
            "user_id": user_id,
            "session_id": end_request.session_id,
            "score": result.score,
            "total_questions": result.total_questions,
            "event_type": "quiz_end_success",
        },
    )

    return result
