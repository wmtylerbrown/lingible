"""Quiz models for slang learning games."""

from typing import Dict, List, Optional

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .base import LingibleBaseModel


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


class QuizOption(LingibleBaseModel):
    """Single quiz answer option."""

    id: str = Field(description="Option identifier (a, b, c, d)")
    text: str = Field(description="The answer text")
    is_correct: Optional[bool] = Field(
        default=None,
        description="Whether this option is correct (only included in results, not in challenge)",
    )


class QuizQuestion(LingibleBaseModel):
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


class QuizQuestionResult(LingibleBaseModel):
    """Result for a single question."""

    question_id: str = Field(description="Question ID")
    slang_term: str = Field(description="The slang term")
    your_answer: str = Field(description="User's selected answer")
    correct_answer: str = Field(description="Correct answer option ID")
    is_correct: bool = Field(description="Whether the user got it right")
    explanation: str = Field(description="Full explanation of the term")


class QuizResult(LingibleBaseModel):
    """Complete quiz results."""

    session_id: str = Field(description="Session ID")
    score: float = Field(description="Total score achieved")
    total_possible: float = Field(description="Maximum possible score")
    correct_count: int = Field(description="Number of correct answers")
    total_questions: int = Field(description="Total number of questions")
    time_taken_seconds: float = Field(description="Time taken to complete")
    share_text: str = Field(description="Text for sharing results")
    share_url: Optional[str] = Field(
        default=None, description="URL for sharing results (future feature)"
    )


class QuizHistory(LingibleBaseModel):
    """User's quiz history summary."""

    user_id: str = Field(description="User ID")
    total_quizzes: int = Field(description="Total quizzes taken")
    average_score: float = Field(description="Average score across all quizzes")
    best_score: float = Field(description="Best score achieved")
    total_correct: int = Field(description="Total correct answers")
    total_questions: int = Field(description="Total questions answered")
    accuracy_rate: float = Field(description="Overall accuracy percentage")
    quizzes_today: int = Field(description="Number of quizzes taken today")
    can_take_quiz: bool = Field(description="Whether user can take another quiz")
    reason: Optional[str] = Field(
        default=None,
        description="Reason if user cannot take quiz (e.g., 'Daily limit reached')",
    )


# ===== Stateless Quiz API Models =====


class QuizQuestionResponse(LingibleBaseModel):
    """Response for GET /quiz/question - single question with session info."""

    session_id: str = Field(description="Quiz session identifier")
    question: QuizQuestion = Field(description="The quiz question")


class QuizAnswerRequest(BaseModel):
    """Request to submit answer for one question."""

    session_id: str = Field(description="Quiz session identifier")
    question_id: str = Field(description="ID of the question being answered")
    selected_option: str = Field(description="Selected option ID (a, b, c, d)")
    time_taken_seconds: float = Field(
        ge=0.0, description="Time taken to answer (in seconds)"
    )


class QuizAnswerResponse(LingibleBaseModel):
    """Response for POST /quiz/answer - immediate feedback."""

    is_correct: bool = Field(description="Whether the answer was correct")
    points_earned: float = Field(description="Points earned for this question")
    explanation: str = Field(description="Explanation of the correct answer")
    running_stats: "QuizSessionProgress" = Field(
        description="Current session statistics"
    )


class QuizSessionProgress(LingibleBaseModel):
    """Current quiz session progress statistics."""

    questions_answered: int = Field(description="Number of questions answered")
    correct_count: int = Field(description="Number of correct answers")
    total_score: float = Field(description="Total score accumulated")
    accuracy: float = Field(
        ge=0.0, le=1.0, description="Current accuracy rate (0.0 to 1.0)"
    )
    time_spent_seconds: float = Field(description="Total time spent on quiz so far")


class QuizSessionStatus(str, Enum):
    """Quiz session lifecycle status."""

    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class QuizSessionRecord(LingibleBaseModel):
    """Stored quiz session record."""

    session_id: str = Field(description="Session identifier")
    user_id: str = Field(description="User identifier")
    difficulty: QuizDifficulty = Field(
        default=QuizDifficulty.BEGINNER, description="Selected quiz difficulty"
    )
    status: QuizSessionStatus = Field(
        default=QuizSessionStatus.ACTIVE, description="Session status"
    )
    questions_answered: int = Field(
        default=0, ge=0, description="Number of questions answered"
    )
    correct_count: int = Field(
        default=0, ge=0, description="Number of questions answered correctly"
    )
    total_score: float = Field(
        default=0.0, ge=0.0, description="Accumulated score during session"
    )
    correct_answers: Dict[str, str] = Field(
        default_factory=dict, description="Map of question_id to correct answer"
    )
    term_names: Dict[str, str] = Field(
        default_factory=dict, description="Map of question_id to slang term name"
    )
    used_wrong_options: List[str] = Field(
        default_factory=list, description="Answer options used as distractors"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the session started"
    )
    last_activity: datetime = Field(
        default_factory=datetime.utcnow,
        description="Most recent interaction timestamp",
    )


class QuizStats(LingibleBaseModel):
    """Aggregated quiz statistics for a user."""

    total_quizzes: int = Field(default=0, ge=0, description="Total quizzes taken")
    total_correct: int = Field(default=0, ge=0, description="Total correct answers")
    total_questions: int = Field(default=0, ge=0, description="Total questions faced")
    average_score: float = Field(
        default=0.0, ge=0.0, description="Average score percentage"
    )
    best_score: float = Field(
        default=0.0, ge=0.0, description="Best score percentage achieved"
    )
    accuracy_rate: float = Field(
        default=0.0,
        ge=0.0,
        description="Ratio of correct answers to questions attempted",
    )


class QuizEndRequest(BaseModel):
    """Request to end quiz session."""

    session_id: str = Field(description="Quiz session identifier")


# Update forward references for string annotations
QuizAnswerResponse.model_rebuild()
