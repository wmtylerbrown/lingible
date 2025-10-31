"""Quiz models for slang learning games."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class QuizDifficulty(str, Enum):
    """Quiz difficulty levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QuizCategory(str, Enum):
    """Quiz categories for slang terms."""

    APPROVAL = "approval"
    DISAPPROVAL = "disapproval"
    EMOTION = "emotion"
    FOOD = "food"
    APPEARANCE = "appearance"
    SOCIAL = "social"
    AUTHENTICITY = "authenticity"
    INTENSITY = "intensity"
    GENERAL = "general"


class ChallengeType(str, Enum):
    """Types of quiz challenges."""

    MULTIPLE_CHOICE = "multiple_choice"
    # Future: DECODE_MESSAGE, TRUE_FALSE, MIXED


class QuizOption(BaseModel):
    """Single quiz answer option."""

    id: str = Field(description="Option identifier (a, b, c, d)")
    text: str = Field(description="The answer text")
    is_correct: Optional[bool] = Field(
        default=None,
        description="Whether this option is correct (only included in results, not in challenge)",
    )


class QuizQuestion(BaseModel):
    """Single quiz question."""

    question_id: str = Field(description="Unique question identifier")
    slang_term: str = Field(description="The slang term being tested")
    question_text: str = Field(
        description="The question text (e.g., 'What does 'bussin' mean?')"
    )
    options: List[QuizOption] = Field(description="Available answer options")
    context_hint: Optional[str] = Field(
        default=None, description="Example usage of the slang term"
    )
    explanation: Optional[str] = Field(
        default=None, description="Explanation of the term (only included in results)"
    )


class QuizChallenge(BaseModel):
    """A quiz challenge sent to the user."""

    challenge_id: str = Field(description="Unique challenge identifier")
    challenge_type: ChallengeType = Field(description="Type of quiz challenge")
    difficulty: QuizDifficulty = Field(description="Difficulty level")
    time_limit_seconds: int = Field(description="Time limit for completing the quiz")
    questions: List[QuizQuestion] = Field(description="List of quiz questions")
    scoring: Dict[str, Any] = Field(description="Scoring configuration")
    expires_at: datetime = Field(description="When the challenge expires")


class QuizAnswer(BaseModel):
    """User's answer to a single question."""

    question_id: str = Field(description="ID of the question being answered")
    selected: str = Field(description="Selected option ID (a, b, c, d)")


class QuizSubmissionRequest(BaseModel):
    """Request to submit quiz answers."""

    challenge_id: str = Field(description="ID of the challenge being submitted")
    answers: List[QuizAnswer] = Field(description="User's answers")
    time_taken_seconds: int = Field(description="Time taken to complete the quiz")


class QuizQuestionResult(BaseModel):
    """Result for a single question."""

    question_id: str = Field(description="Question ID")
    slang_term: str = Field(description="The slang term")
    your_answer: str = Field(description="User's selected answer")
    correct_answer: str = Field(description="Correct answer option ID")
    is_correct: bool = Field(description="Whether the user got it right")
    explanation: str = Field(description="Full explanation of the term")


class QuizResult(BaseModel):
    """Complete quiz results."""

    challenge_id: str = Field(description="Challenge ID")
    score: int = Field(description="Total score achieved")
    total_possible: int = Field(description="Maximum possible score")
    correct_count: int = Field(description="Number of correct answers")
    total_questions: int = Field(description="Total number of questions")
    time_taken_seconds: int = Field(description="Time taken to complete")
    time_bonus_points: int = Field(description="Bonus points for fast completion")
    results: List[QuizQuestionResult] = Field(description="Per-question results")
    share_text: str = Field(description="Text for sharing results")
    share_url: Optional[str] = Field(
        default=None, description="URL for sharing results (future feature)"
    )


class QuizHistory(BaseModel):
    """User's quiz history summary."""

    user_id: str = Field(description="User ID")
    total_quizzes: int = Field(description="Total quizzes taken")
    average_score: float = Field(description="Average score across all quizzes")
    best_score: int = Field(description="Best score achieved")
    total_correct: int = Field(description="Total correct answers")
    total_questions: int = Field(description="Total questions answered")
    accuracy_rate: float = Field(description="Overall accuracy percentage")
    quizzes_today: int = Field(description="Number of quizzes taken today")
    can_take_quiz: bool = Field(description="Whether user can take another quiz")
    reason: Optional[str] = Field(
        default=None,
        description="Reason if user cannot take quiz (e.g., 'Daily limit reached')",
    )


class QuizChallengeRequest(BaseModel):
    """Request parameters for generating a quiz."""

    difficulty: Optional[QuizDifficulty] = Field(
        default=QuizDifficulty.BEGINNER, description="Desired difficulty level"
    )
    challenge_type: Optional[ChallengeType] = Field(
        default=ChallengeType.MULTIPLE_CHOICE, description="Type of challenge"
    )
    question_count: Optional[int] = Field(
        default=10, description="Number of questions in the quiz"
    )
