"""Tests for quiz models."""

import pytest
from datetime import datetime, timezone

from models.quiz import (
    QuizDifficulty,
    QuizCategory,
    ChallengeType,
    QuizOption,
    QuizQuestion,
    QuizChallenge,
    QuizAnswer,
    QuizSubmissionRequest,
    QuizQuestionResult,
    QuizResult,
    QuizHistory,
    QuizChallengeRequest,
)


class TestQuizModels:
    """Test quiz model validation and behavior."""

    def test_quiz_difficulty_enum(self):
        """Test QuizDifficulty enum values."""
        assert QuizDifficulty.BEGINNER == "beginner"
        assert QuizDifficulty.INTERMEDIATE == "intermediate"
        assert QuizDifficulty.ADVANCED == "advanced"

    def test_quiz_category_enum(self):
        """Test QuizCategory enum values."""
        assert QuizCategory.APPROVAL == "approval"
        assert QuizCategory.DISAPPROVAL == "disapproval"
        assert QuizCategory.EMOTION == "emotion"
        assert QuizCategory.FOOD == "food"
        assert QuizCategory.APPEARANCE == "appearance"
        assert QuizCategory.SOCIAL == "social"
        assert QuizCategory.AUTHENTICITY == "authenticity"
        assert QuizCategory.INTENSITY == "intensity"
        assert QuizCategory.GENERAL == "general"

    def test_challenge_type_enum(self):
        """Test ChallengeType enum values."""
        assert ChallengeType.MULTIPLE_CHOICE == "multiple_choice"

    def test_quiz_option_model(self):
        """Test QuizOption model."""
        option = QuizOption(
            id="a",
            text="Really good",
            is_correct=True
        )

        assert option.id == "a"
        assert option.text == "Really good"
        assert option.is_correct is True

    def test_quiz_question_model(self):
        """Test QuizQuestion model."""
        options = [
            QuizOption(id="a", text="Really good"),
            QuizOption(id="b", text="Bad"),
            QuizOption(id="c", text="Okay"),
            QuizOption(id="d", text="Average"),
        ]

        question = QuizQuestion(
            question_id="q_123",
            slang_term="bussin",
            question_text="What does 'bussin' mean?",
            options=options,
            context_hint="That pizza was bussin!",
            explanation="Bussin means really good, especially for food."
        )

        assert question.question_id == "q_123"
        assert question.slang_term == "bussin"
        assert question.question_text == "What does 'bussin' mean?"
        assert len(question.options) == 4
        assert question.context_hint == "That pizza was bussin!"
        assert question.explanation == "Bussin means really good, especially for food."

    def test_quiz_challenge_model(self):
        """Test QuizChallenge model."""
        options = [
            QuizOption(id="a", text="Really good"),
            QuizOption(id="b", text="Bad"),
        ]

        questions = [
            QuizQuestion(
                question_id="q1",
                slang_term="bussin",
                question_text="What does 'bussin' mean?",
                options=options
            )
        ]

        challenge = QuizChallenge(
            challenge_id="quiz_123",
            challenge_type=ChallengeType.MULTIPLE_CHOICE,
            difficulty=QuizDifficulty.BEGINNER,
            time_limit_seconds=60,
            questions=questions,
            scoring={"points_per_correct": 10, "time_bonus": True},
            expires_at=datetime.now(timezone.utc)
        )

        assert challenge.challenge_id == "quiz_123"
        assert challenge.challenge_type == ChallengeType.MULTIPLE_CHOICE
        assert challenge.difficulty == QuizDifficulty.BEGINNER
        assert challenge.time_limit_seconds == 60
        assert len(challenge.questions) == 1
        assert challenge.scoring["points_per_correct"] == 10

    def test_quiz_answer_model(self):
        """Test QuizAnswer model."""
        answer = QuizAnswer(
            question_id="q_123",
            selected="a"
        )

        assert answer.question_id == "q_123"
        assert answer.selected == "a"

    def test_quiz_submission_request_model(self):
        """Test QuizSubmissionRequest model."""
        answers = [
            QuizAnswer(question_id="q1", selected="a"),
            QuizAnswer(question_id="q2", selected="b"),
        ]

        submission = QuizSubmissionRequest(
            challenge_id="quiz_123",
            answers=answers,
            time_taken_seconds=45
        )

        assert submission.challenge_id == "quiz_123"
        assert len(submission.answers) == 2
        assert submission.time_taken_seconds == 45

    def test_quiz_question_result_model(self):
        """Test QuizQuestionResult model."""
        result = QuizQuestionResult(
            question_id="q_123",
            slang_term="bussin",
            your_answer="a",
            correct_answer="a",
            is_correct=True,
            explanation="Bussin means really good, especially for food."
        )

        assert result.question_id == "q_123"
        assert result.slang_term == "bussin"
        assert result.your_answer == "a"
        assert result.correct_answer == "a"
        assert result.is_correct is True
        assert "really good" in result.explanation.lower()

    def test_quiz_result_model(self):
        """Test QuizResult model."""
        question_results = [
            QuizQuestionResult(
                question_id="q1",
                slang_term="bussin",
                your_answer="a",
                correct_answer="a",
                is_correct=True,
                explanation="Bussin means really good."
            ),
            QuizQuestionResult(
                question_id="q2",
                slang_term="cap",
                your_answer="b",
                correct_answer="a",
                is_correct=False,
                explanation="Cap means lie."
            )
        ]

        result = QuizResult(
            challenge_id="quiz_123",
            score=15,
            total_possible=20,
            correct_count=1,
            total_questions=2,
            time_taken_seconds=45,
            time_bonus_points=5,
            results=question_results,
            share_text="I scored 15/20 on the Lingible Slang Quiz!",
            share_url="https://lingible.com/quiz/123"
        )

        assert result.challenge_id == "quiz_123"
        assert result.score == 15
        assert result.total_possible == 20
        assert result.correct_count == 1
        assert result.total_questions == 2
        assert result.time_taken_seconds == 45
        assert result.time_bonus_points == 5
        assert len(result.results) == 2
        assert "15/20" in result.share_text
        assert result.share_url == "https://lingible.com/quiz/123"

    def test_quiz_history_model(self):
        """Test QuizHistory model."""
        history = QuizHistory(
            user_id="user_123",
            total_quizzes=10,
            average_score=85.5,
            best_score=100,
            total_correct=85,
            total_questions=100,
            accuracy_rate=0.85,
            quizzes_today=3,
            can_take_quiz=True,
            reason=None
        )

        assert history.user_id == "user_123"
        assert history.total_quizzes == 10
        assert history.average_score == 85.5
        assert history.best_score == 100
        assert history.total_correct == 85
        assert history.total_questions == 100
        assert history.accuracy_rate == 0.85
        assert history.quizzes_today == 3
        assert history.can_take_quiz is True
        assert history.reason is None

    def test_quiz_history_cannot_take_quiz(self):
        """Test QuizHistory when user cannot take quiz."""
        history = QuizHistory(
            user_id="user_123",
            total_quizzes=5,
            average_score=75.0,
            best_score=90,
            total_correct=38,
            total_questions=50,
            accuracy_rate=0.76,
            quizzes_today=3,
            can_take_quiz=False,
            reason="Daily limit of 3 quizzes reached. Upgrade to Premium for unlimited quizzes!"
        )

        assert history.can_take_quiz is False
        assert "limit" in history.reason.lower()
        assert "upgrade" in history.reason.lower()

    def test_quiz_challenge_request_model(self):
        """Test QuizChallengeRequest model with defaults."""
        request = QuizChallengeRequest()

        assert request.difficulty == QuizDifficulty.BEGINNER
        assert request.challenge_type == ChallengeType.MULTIPLE_CHOICE
        assert request.question_count == 10

    def test_quiz_challenge_request_model_custom(self):
        """Test QuizChallengeRequest model with custom values."""
        request = QuizChallengeRequest(
            difficulty=QuizDifficulty.ADVANCED,
            challenge_type=ChallengeType.MULTIPLE_CHOICE,
            question_count=15
        )

        assert request.difficulty == QuizDifficulty.ADVANCED
        assert request.challenge_type == ChallengeType.MULTIPLE_CHOICE
        assert request.question_count == 15

    def test_quiz_option_without_is_correct(self):
        """Test QuizOption without is_correct field (for challenges)."""
        option = QuizOption(
            id="a",
            text="Really good"
        )

        assert option.id == "a"
        assert option.text == "Really good"
        assert option.is_correct is None

    def test_quiz_question_without_explanation(self):
        """Test QuizQuestion without explanation (for challenges)."""
        options = [QuizOption(id="a", text="Really good")]

        question = QuizQuestion(
            question_id="q_123",
            slang_term="bussin",
            question_text="What does 'bussin' mean?",
            options=options
        )

        assert question.explanation is None

    def test_quiz_result_without_share_url(self):
        """Test QuizResult without share_url."""
        result = QuizResult(
            challenge_id="quiz_123",
            score=10,
            total_possible=10,
            correct_count=1,
            total_questions=1,
            time_taken_seconds=30,
            time_bonus_points=0,
            results=[],
            share_text="I scored 10/10!"
        )

        assert result.share_url is None
