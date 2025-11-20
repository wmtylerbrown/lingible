"""Lambda handler for quiz answer endpoint (stateless per-question API)."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import QuizAnswerEvent
from models.quiz import QuizAnswerResponse
from services.quiz_service import QuizService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import QuizAnswerEnvelope
from utils.smart_logger import logger


# Initialize service at module level (Lambda container reuse)
quiz_service = QuizService()


# Stateless per-question answer endpoint (new API)
@tracer.trace_lambda
@event_parser(model=QuizAnswerEvent, envelope=QuizAnswerEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: QuizAnswerEvent, context: LambdaContext) -> QuizAnswerResponse:
    """Handle POST /quiz/answer - submit answer for one question (stateless API)."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Get answer request from the parsed request body
    answer_request = event.request_body

    # Debug logging for development
    logger.log_debug(
        "Quiz answer submission started",
        {
            "user_id": user_id,
            "session_id": answer_request.session_id,
            "question_id": answer_request.question_id,
            "selected_option": answer_request.selected_option,
            "time_taken_seconds": answer_request.time_taken_seconds,
            "event_type": "quiz_answer_submission",
        },
    )

    # Submit the answer and get immediate feedback
    response = quiz_service.submit_answer(user_id, answer_request)

    # Debug logging for successful response
    logger.log_debug(
        "Quiz answer processed successfully",
        {
            "user_id": user_id,
            "session_id": answer_request.session_id,
            "is_correct": response.is_correct,
            "points_earned": response.points_earned,
            "event_type": "quiz_answer_success",
        },
    )

    # Return the response directly - decorator handles the API response creation
    return response
