"""Lambda handler for quiz progress endpoint (stateless per-question API)."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import QuizProgressEvent
from models.quiz import QuizSessionProgress
from services.quiz_service import QuizService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import QuizProgressEnvelope
from utils.smart_logger import logger
from utils.exceptions import ValidationError


# Initialize service at module level (Lambda container reuse)
quiz_service = QuizService()


# Stateless quiz progress endpoint (new API)
@tracer.trace_lambda
@event_parser(model=QuizProgressEvent, envelope=QuizProgressEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: QuizProgressEvent, context: LambdaContext) -> QuizSessionProgress:
    """Handle GET /quiz/progress - get current session progress (stateless API)."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Get session_id from query parameter
    session_id = event.session_id
    if not session_id:
        raise ValidationError("session_id query parameter is required")

    logger.log_debug(
        "Quiz progress request",
        {
            "user_id": user_id,
            "session_id": session_id,
            "event_type": "quiz_progress_request",
        },
    )

    # Get session progress
    progress = quiz_service.get_session_progress(user_id, session_id)

    logger.log_debug(
        "Quiz progress retrieved",
        {
            "user_id": user_id,
            "session_id": session_id,
            "questions_answered": progress.questions_answered,
            "event_type": "quiz_progress_success",
        },
    )

    return progress
