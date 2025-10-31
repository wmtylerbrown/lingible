"""Service for quiz generation, scoring, and history tracking."""

import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import List

from models.quiz import (
    QuizChallenge,
    QuizChallengeRequest,
    QuizQuestion,
    QuizOption,
    QuizSubmissionRequest,
    QuizResult,
    QuizQuestionResult,
    QuizHistory,
    QuizDifficulty,
    ChallengeType,
)
from models.config import QuizConfig
from models.users import UserTier
from repositories.slang_term_repository import SlangTermRepository
from services.user_service import UserService
from utils.config import get_config_service
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.exceptions import ValidationError, InsufficientPermissionsError


class QuizService:
    """Service for quiz generation, scoring, and history tracking."""

    def __init__(self):
        self.repository = SlangTermRepository()
        self.user_service = UserService()
        self.config = get_config_service().get_config(QuizConfig)
        self._active_challenges = {}  # In-memory cache for challenge validation

    @tracer.trace_method("check_quiz_eligibility")
    def check_quiz_eligibility(self, user_id: str) -> QuizHistory:
        """Check if user can take a quiz and return their stats."""
        user = self.user_service.get_user(user_id)
        is_premium = user is not None and user.tier != UserTier.FREE

        # Get today's quiz count
        today = datetime.now(timezone.utc).date().isoformat()
        quizzes_today = self.repository.get_daily_quiz_count(user_id, today)

        # Check eligibility
        can_take_quiz = is_premium or quizzes_today < self.config.free_daily_limit
        reason = None
        if not can_take_quiz:
            reason = f"Daily limit of {self.config.free_daily_limit} quizzes reached. Upgrade to Premium for unlimited quizzes!"

        # Get user stats
        stats = self.repository.get_user_quiz_stats(user_id)

        return QuizHistory(
            user_id=user_id,
            total_quizzes=stats.get("total_quizzes", 0),
            average_score=stats.get("average_score", 0.0),
            best_score=stats.get("best_score", 0),
            total_correct=stats.get("total_correct", 0),
            total_questions=stats.get("total_questions", 0),
            accuracy_rate=stats.get("accuracy_rate", 0.0),
            quizzes_today=quizzes_today,
            can_take_quiz=can_take_quiz,
            reason=reason,
        )

    @tracer.trace_method("generate_challenge")
    def generate_challenge(
        self, user_id: str, request: QuizChallengeRequest
    ) -> QuizChallenge:
        """Generate a new quiz challenge."""

        # Check eligibility
        eligibility = self.check_quiz_eligibility(user_id)
        if not eligibility.can_take_quiz:
            raise InsufficientPermissionsError(
                eligibility.reason or "Quiz not available"
            )

        # Extract values with defaults (handle Optional fields)
        difficulty = request.difficulty or QuizDifficulty.BEGINNER
        challenge_type = request.challenge_type or ChallengeType.MULTIPLE_CHOICE
        question_count = request.question_count or 10

        # Get quiz-eligible terms
        terms = self.repository.get_quiz_eligible_terms(
            difficulty=difficulty,
            limit=question_count * 3,  # Get extras to ensure variety
        )

        if len(terms) < question_count:
            raise ValidationError(
                f"Not enough terms available for difficulty {difficulty}"
            )

        # Randomly select terms
        selected_terms = random.sample(terms, question_count)

        # Format questions
        questions = []
        correct_answers = {}
        term_names = {}

        for term in selected_terms:
            if challenge_type == ChallengeType.MULTIPLE_CHOICE:
                question, correct_option = self._format_multiple_choice(term)
                questions.append(question)
                correct_answers[question.question_id] = correct_option
                term_names[question.question_id] = term["slang_term"]

        # Create challenge
        challenge_id = f"quiz_{uuid.uuid4().hex[:16]}"
        challenge = QuizChallenge(
            challenge_id=challenge_id,
            challenge_type=challenge_type,
            difficulty=difficulty,
            time_limit_seconds=self.config.time_limit_seconds,
            questions=questions,
            scoring={
                "points_per_correct": self.config.points_per_correct,
                "time_bonus": self.config.enable_time_bonus,
            },
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Cache challenge for validation (expires after 1 hour)
        self._active_challenges[challenge_id] = {
            "user_id": user_id,
            "correct_answers": correct_answers,
            "expires_at": challenge.expires_at,
            "terms": term_names,
            "difficulty": difficulty,
        }

        logger.log_business_event(
            "quiz_challenge_generated",
            {
                "user_id": user_id,
                "challenge_id": challenge_id,
                "difficulty": difficulty,
                "question_count": len(questions),
            },
        )

        return challenge

    def _format_multiple_choice(self, term: dict) -> tuple[QuizQuestion, str]:
        """Format a term as multiple choice question. Returns (question, correct_option_id)."""
        wrong_options = term.get("quiz_wrong_options", [])

        # If no pre-generated options, generate them
        if not wrong_options or len(wrong_options) < 3:
            wrong_options = self._generate_wrong_options(term, wrong_options)

        # Ensure we have exactly 3 wrong options
        wrong_options = wrong_options[:3]

        # Create options (mark correct answer for internal tracking)
        all_options = [
            QuizOption(id="a", text=term["meaning"]),
            QuizOption(id="b", text=wrong_options[0]),
            QuizOption(id="c", text=wrong_options[1]),
            QuizOption(id="d", text=wrong_options[2]),
        ]

        # Shuffle options but remember which one is correct
        correct_text = term["meaning"]
        random.shuffle(all_options)

        # Find the correct option ID after shuffling
        correct_option_id = None
        for option in all_options:
            if option.text == correct_text:
                correct_option_id = option.id
                break

        question = QuizQuestion(
            question_id=f"q_{uuid.uuid4().hex[:12]}",
            slang_term=term["slang_term"],
            question_text=f"What does '{term['slang_term']}' mean?",
            options=all_options,
            context_hint=term.get("example_usage"),
        )

        return question, correct_option_id or "a"

    def _generate_wrong_options(
        self, term: dict, existing: List[str] = []
    ) -> List[str]:
        """Generate plausible wrong answers using category-based approach."""
        needed = 3 - len(existing)

        # Strategy A: Try to get from similar category terms first
        similar_terms = self.repository.get_terms_by_category(
            term.get("quiz_category", "general"), limit=10
        )

        category_options = [
            t["meaning"]
            for t in similar_terms
            if t["slang_term"] != term["slang_term"]
            and t["meaning"] != term["meaning"]
            and t["meaning"] not in existing
        ]

        wrong_options = existing + category_options[:needed]

        # If still not enough, use generic fallbacks
        if len(wrong_options) < 3:
            fallbacks = [
                "Very busy",
                "Broken or damaged",
                "On a bus",
                "Confused",
                "Tired",
                "Excited",
                "Angry",
                "Happy",
                "Sad",
                "Cool",
                "Weird",
                "Funny",
                "Serious",
                "Fast",
                "Slow",
                "Big",
                "Small",
                "Hot",
                "Cold",
            ]
            wrong_options.extend(
                [f for f in fallbacks if f not in wrong_options][
                    : 3 - len(wrong_options)
                ]
            )

        return wrong_options[:3]

    @tracer.trace_method("submit_quiz")
    def submit_quiz(
        self, user_id: str, submission: QuizSubmissionRequest
    ) -> QuizResult:
        """Grade a quiz submission and return results."""

        # Validate challenge exists and belongs to user
        if submission.challenge_id not in self._active_challenges:
            raise ValidationError("Invalid or expired challenge ID")

        challenge_data = self._active_challenges[submission.challenge_id]

        if challenge_data["user_id"] != user_id:
            raise ValidationError("Challenge does not belong to this user")

        if datetime.now(timezone.utc) > challenge_data["expires_at"]:
            del self._active_challenges[submission.challenge_id]
            raise ValidationError("Challenge has expired")

        # Grade answers
        correct_answers = challenge_data["correct_answers"]
        term_names = challenge_data["terms"]
        results = []
        correct_count = 0

        for answer in submission.answers:
            is_correct = answer.selected == correct_answers.get(answer.question_id)
            if is_correct:
                correct_count += 1

            # Get term details for explanation
            term = self.repository.get_term_by_slang(term_names[answer.question_id])

            results.append(
                QuizQuestionResult(
                    question_id=answer.question_id,
                    slang_term=term_names[answer.question_id],
                    your_answer=answer.selected,
                    correct_answer=correct_answers[answer.question_id],
                    is_correct=is_correct,
                    explanation=term.get("meaning", "") if term else "Term not found",
                )
            )

        # Calculate score
        base_score = correct_count * self.config.points_per_correct
        time_bonus = 0
        if (
            self.config.enable_time_bonus
            and submission.time_taken_seconds < self.config.time_limit_seconds
        ):
            time_bonus = int(
                (self.config.time_limit_seconds - submission.time_taken_seconds) / 6
            )  # 1 point per 6 seconds saved

        total_score = base_score + time_bonus
        total_possible = (
            len(submission.answers) * self.config.points_per_correct + 10
        )  # Max 10 time bonus

        # Save to history
        self.repository.save_quiz_result(
            user_id,
            {
                "quiz_id": submission.challenge_id,
                "score": total_score,
                "total_possible": total_possible,
                "correct_count": correct_count,
                "total_questions": len(submission.answers),
                "time_taken_seconds": submission.time_taken_seconds,
                "difficulty": challenge_data.get("difficulty", "beginner"),
                "challenge_type": "multiple_choice",
            },
        )

        # Increment daily count
        self.repository.increment_daily_quiz_count(user_id)

        # Update quiz statistics for terms
        for result in results:
            self.repository.update_quiz_statistics(result.slang_term, result.is_correct)

        # Clean up challenge
        del self._active_challenges[submission.challenge_id]

        # Generate share text
        accuracy = int((correct_count / len(submission.answers)) * 100)
        share_text = f"I scored {total_score}/{total_possible} on the Lingible Slang Quiz! I got {correct_count}/{len(submission.answers)} right ({accuracy}% accuracy). Can you beat me? 🔥"

        logger.log_business_event(
            "quiz_completed",
            {
                "user_id": user_id,
                "score": total_score,
                "correct_count": correct_count,
                "total_questions": len(submission.answers),
            },
        )

        return QuizResult(
            challenge_id=submission.challenge_id,
            score=total_score,
            total_possible=total_possible,
            correct_count=correct_count,
            total_questions=len(submission.answers),
            time_taken_seconds=submission.time_taken_seconds,
            time_bonus_points=time_bonus,
            results=results,
            share_text=share_text,
        )
