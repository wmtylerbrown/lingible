"""Lambda handler for quiz question endpoint (stateless per-question API)."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import QuizQuestionEvent
from models.quiz import QuizQuestionResponse, QuizDifficulty
from services.quiz_service import QuizService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import QuizQuestionEnvelope
from utils.smart_logger import logger


# Initialize service at module level (Lambda container reuse)
quiz_service = QuizService()


# Stateless per-question endpoint (new API)
@tracer.trace_lambda
@event_parser(model=QuizQuestionEvent, envelope=QuizQuestionEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: QuizQuestionEvent, context: LambdaContext) -> QuizQuestionResponse:
    """Handle GET /quiz/question - get next question (stateless API)."""
    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Parse difficulty from query parameter
    difficulty = QuizDifficulty.BEGINNER
    if event.difficulty:
        try:
            difficulty = QuizDifficulty(event.difficulty)
        except ValueError:
            difficulty = QuizDifficulty.BEGINNER

    logger.log_debug(
        "Quiz question request",
        {
            "user_id": user_id,
            "difficulty": difficulty.value,
            "event_type": "quiz_question_request",
        },
    )

    # Get next question
    response = quiz_service.get_next_question(user_id, difficulty)

    logger.log_debug(
        "Quiz question generated",
        {
            "user_id": user_id,
            "session_id": response.session_id,
            "question_id": response.question.question_id,
            "event_type": "quiz_question_success",
        },
    )

    return response
