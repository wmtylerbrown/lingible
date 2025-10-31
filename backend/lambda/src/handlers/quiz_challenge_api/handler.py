"""Lambda handler for quiz challenge endpoint."""

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext

from models.events import QuizChallengeEvent
from models.quiz import (
    QuizChallengeRequest,
    QuizChallenge,
    QuizDifficulty,
    ChallengeType,
)
from services.quiz_service import QuizService
from utils.tracing import tracer
from utils.decorators import api_handler, extract_user_from_parsed_data
from utils.envelopes import QuizChallengeEnvelope
from utils.smart_logger import logger


# Initialize service at module level (Lambda container reuse)
quiz_service = QuizService()


# Lambda handler entry point - API Gateway authorizer handles authentication
@tracer.trace_lambda
@event_parser(model=QuizChallengeEvent, envelope=QuizChallengeEnvelope)
@api_handler(extract_user_id=extract_user_from_parsed_data)
def handler(event: QuizChallengeEvent, context: LambdaContext) -> QuizChallenge:
    """Handle quiz challenge requests from mobile app."""

    # Get user ID from the event (guaranteed by envelope)
    user_id = event.user_id

    # Create QuizChallengeRequest from parsed query parameters
    request = QuizChallengeRequest(
        difficulty=QuizDifficulty(event.difficulty) if event.difficulty else None,
        challenge_type=(
            ChallengeType(event.challenge_type) if event.challenge_type else None
        ),
        question_count=event.question_count,
    )

    # Debug logging for development
    logger.log_debug(
        "Quiz challenge request started",
        {
            "user_id": user_id,
            "difficulty": request.difficulty,
            "challenge_type": request.challenge_type,
            "question_count": request.question_count,
            "event_type": "quiz_challenge_request",
        },
    )

    # Generate the quiz challenge
    challenge = quiz_service.generate_challenge(user_id, request)

    # Debug logging for successful response
    logger.log_debug(
        "Quiz challenge generated successfully",
        {
            "user_id": user_id,
            "challenge_id": challenge.challenge_id,
            "question_count": len(challenge.questions),
            "event_type": "quiz_challenge_success",
        },
    )

    # Return the challenge directly - decorator handles the API response creation
    return challenge
