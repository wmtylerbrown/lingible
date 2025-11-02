"""Service for quiz generation, scoring, and history tracking."""

import uuid
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Set

from models.quiz import (
    QuizQuestion,
    QuizOption,
    QuizResult,
    QuizHistory,
    QuizDifficulty,
    QuizCategory,
    QuizQuestionResponse,
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizSessionProgress,
)
from models.config import QuizConfig
from models.users import UserTier
from repositories.slang_term_repository import SlangTermRepository
from repositories.user_repository import UserRepository
from services.user_service import UserService
from utils.config import get_config_service
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.exceptions import ValidationError, UsageLimitExceededError


class QuizService:
    """Service for quiz generation, scoring, and history tracking."""

    # Class-level cache for wrong answer pools (loaded once per Lambda instance)
    _wrong_answer_pools: Dict[str, List[str]] = {}
    _pools_loaded: bool = False

    def __init__(self):
        self.repository = SlangTermRepository()
        self.user_repository = UserRepository()
        self.user_service = UserService()
        self.config = get_config_service().get_config(QuizConfig)
        self._ensure_pools_loaded()

    # ===== Answer Normalization (Phase 1.5) =====

    def _normalize_answer_text(self, text: str) -> str:
        """Normalize answer text: extract first meaning, standardize formatting."""
        if not text:
            return ""
        # Extract first meaning before semicolon
        normalized = text.split(";")[0].strip()
        # Standardize capitalization: sentence case (first letter uppercase, rest lowercase)
        if normalized:
            normalized = (
                normalized[0].upper() + normalized[1:].lower()
                if len(normalized) > 1
                else normalized.upper()
            )
        return normalized

    # ===== Per-Question Scoring (Phase 2) =====

    def _calculate_question_points(
        self, is_correct: bool, time_taken_seconds: float
    ) -> float:
        """Calculate points earned for a single question based on correctness and time."""
        if not is_correct:
            return 0.0

        max_points = self.config.points_per_correct
        question_time_limit = 30.0  # 30 seconds per question (configurable later)

        # Calculate time ratio (capped at 1.0)
        time_ratio = min(time_taken_seconds / question_time_limit, 1.0)

        # Points decrease linearly: 90% decay, 10% minimum
        # Formula: max_points * (1.0 - time_ratio * 0.9)
        points_earned = max_points * (1.0 - time_ratio * 0.9)

        # Ensure minimum of 1 point
        return max(1.0, round(points_earned, 1))

    @tracer.trace_method("check_quiz_eligibility")
    def check_quiz_eligibility(self, user_id: str) -> QuizHistory:
        """Check if user can take a quiz and return their stats."""
        user = self.user_service.get_user(user_id)
        is_premium = user is not None and user.tier != UserTier.FREE

        # Get today's quiz count
        today = datetime.now(timezone.utc).date().isoformat()
        quizzes_today = self.user_repository.get_daily_quiz_count(user_id, today)

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

    def _format_multiple_choice(
        self, term: dict, used_wrong_options: Set[str]
    ) -> tuple[QuizQuestion, str]:
        """Format a term as multiple choice question. Returns (question, correct_option_id).

        Args:
            term: Term dictionary with meaning, slang_term, etc.
            used_wrong_options: Set of normalized wrong options already used in this session
        """
        # Normalize correct answer
        correct_meaning = self._normalize_answer_text(term["meaning"])

        # Get category for pool lookup
        category = term.get("quiz_category", "general")

        # Get wrong options from category pool
        wrong_options = self._get_wrong_options_from_pool(
            category, used_wrong_options, term["meaning"]
        )

        # Fallback to dynamic generation if pool doesn't have enough options
        if len(wrong_options) < 3:
            wrong_options = self._generate_wrong_options(term, used_wrong_options)

        # Ensure we have exactly 3 wrong options (already normalized from pool)
        if len(wrong_options) < 3:
            raise ValidationError(
                f"Failed to generate enough wrong options. Got {len(wrong_options)}, needed 3"
            )

        normalized_wrong = wrong_options[:3]

        # Create options (all normalized for consistency)
        all_options = [
            QuizOption(id="a", text=correct_meaning),
            QuizOption(id="b", text=normalized_wrong[0]),
            QuizOption(id="c", text=normalized_wrong[1]),
            QuizOption(id="d", text=normalized_wrong[2]),
        ]

        # Shuffle options but remember which one is correct
        random.shuffle(all_options)

        # Find the correct option ID after shuffling
        correct_option_id = None
        for option in all_options:
            if option.text == correct_meaning:
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
        self, term: dict, used_wrong_options: Set[str]
    ) -> List[str]:
        """Generate plausible wrong answers using category-based approach (fallback when pools unavailable).

        Args:
            term: Term dictionary
            used_wrong_options: Set of normalized wrong options already used in session
        """
        needed = 3
        normalized_correct = self._normalize_answer_text(term["meaning"])

        # Strategy A: Try to get from similar category terms first
        similar_terms = self.repository.get_terms_by_category(
            term.get("quiz_category", "general"), limit=20  # Get more for variety
        )

        category_options = []
        for t in similar_terms:
            if t["slang_term"] == term["slang_term"]:
                continue
            normalized_meaning = self._normalize_answer_text(t["meaning"])
            # Avoid correct answer and used options
            if (
                normalized_meaning != normalized_correct
                and normalized_meaning not in used_wrong_options
            ):
                category_options.append(normalized_meaning)
                if len(category_options) >= needed:
                    break

        wrong_options = category_options[:needed]

        # If still not enough, use expanded generic fallbacks (normalized)
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
                "Amazing",
                "Terrible",
                "Average",
                "Perfect",
                "Awkward",
                "Popular",
                "Unpopular",
                "Easy",
                "Difficult",
                "Simple",
                "Complex",
                "True",
                "False",
                "Old",
                "New",
                "Fresh",
                "Stale",
                "Modern",
                "Classic",
                "Unique",
                "Common",
                "Rare",
                "Frequent",
                "Occasional",
            ]

            normalized_fallbacks = [self._normalize_answer_text(f) for f in fallbacks]

            # Filter out already used options and correct answer
            available_fallbacks = [
                f
                for f in normalized_fallbacks
                if f not in wrong_options
                and f != normalized_correct
                and f not in used_wrong_options
            ]

            wrong_options.extend(available_fallbacks[: 3 - len(wrong_options)])

        return wrong_options[:3]

    def _ensure_pools_loaded(self) -> None:
        """Load wrong answer pools from DynamoDB (cached per Lambda instance)."""
        if QuizService._pools_loaded:
            return

        try:
            # Load pools for all categories
            for category in QuizCategory:
                pool = self.repository.get_wrong_answer_pool(category.value)
                if pool:
                    QuizService._wrong_answer_pools[category.value] = pool
                    logger.log_debug(
                        "Loaded wrong answer pool",
                        {"category": category.value, "size": len(pool)},
                    )
                else:
                    # Fallback to generic pool if category pool not found
                    logger.log_debug(
                        f"Wrong answer pool not found for category: {category.value}, using generic pool"
                    )
                    QuizService._wrong_answer_pools[category.value] = []

            QuizService._pools_loaded = True
            logger.log_business_event(
                "wrong_answer_pools_loaded",
                {
                    "categories_loaded": len(QuizService._wrong_answer_pools),
                    "total_options": sum(
                        len(pool) for pool in QuizService._wrong_answer_pools.values()
                    ),
                },
            )
        except Exception as e:
            logger.log_error(e, {"operation": "load_wrong_answer_pools"})
            # Continue with empty pools - will use fallback generation

    def _get_wrong_options_from_pool(
        self, category: str, used_wrong_options: Set[str], correct_answer: str
    ) -> List[str]:
        """Get wrong options from category pool, avoiding duplicates and correct answer."""
        # Get pool for category
        pool = QuizService._wrong_answer_pools.get(category, [])
        if not pool:
            # Fallback to general pool if category pool not available
            pool = QuizService._wrong_answer_pools.get("general", [])

        # Normalize correct answer for comparison
        normalized_correct = self._normalize_answer_text(correct_answer)

        # Filter out correct answer and already used options (pool options are already normalized)
        available = []
        for option in pool:
            normalized_option = self._normalize_answer_text(option)
            if (
                normalized_option != normalized_correct
                and normalized_option not in used_wrong_options
            ):
                available.append(normalized_option)

        # If not enough options in pool, fall back to generic generation
        if len(available) < 3:
            logger.log_debug(
                "Not enough options in pool, using fallback generation",
                {"category": category, "available": len(available)},
            )
            return []

        # Shuffle and return 3 random options
        random.shuffle(available)
        return available[:3]

    # ===== Stateless Quiz API Methods =====

    @tracer.trace_method("check_question_eligibility")
    def check_question_eligibility(self, user_id: str) -> bool:
        """Check if user can answer another question (free tier daily limit)."""
        user = self.user_service.get_user(user_id)
        is_premium = user is not None and user.tier != UserTier.FREE

        if is_premium:
            return True

        # Check daily question count (not quiz count)
        today = datetime.now(timezone.utc).date().isoformat()
        questions_today = self.user_repository.get_daily_quiz_count(user_id, today)

        # Free tier: limit total questions per day
        return questions_today < self.config.free_daily_limit

    @tracer.trace_method("get_next_question")
    def get_next_question(
        self, user_id: str, difficulty: Optional[QuizDifficulty] = None
    ) -> QuizQuestionResponse:
        """Get next question for user, creating session if needed."""
        difficulty = difficulty or QuizDifficulty.BEGINNER

        # Check if user can answer another question (before creating session)
        if not self.check_question_eligibility(user_id):
            today = datetime.now(timezone.utc).date().isoformat()
            questions_today = self.user_repository.get_daily_quiz_count(user_id, today)
            raise UsageLimitExceededError(
                limit_type="quiz_questions",
                current_usage=questions_today,
                limit=self.config.free_daily_limit,
                message=f"Daily limit of {self.config.free_daily_limit} questions reached. Upgrade to Premium for unlimited questions!",
            )

        # Get or create session
        session = self.repository.get_active_quiz_session(user_id)
        if not session:
            # Create new session
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            self.repository.create_quiz_session(
                session_id=session_id,
                user_id=user_id,
                difficulty=difficulty.value,
            )
            session = self.repository.get_quiz_session(session_id)
            if not session:
                raise ValidationError("Failed to create quiz session")
        else:
            session_id = session["session_id"]
            # Ensure difficulty matches (use session difficulty)
            difficulty = QuizDifficulty(session.get("difficulty", "beginner"))

        # Get used wrong options from session to avoid duplicates
        used_wrong_options_list = session.get("used_wrong_options", [])
        used_wrong_options: Set[str] = set(used_wrong_options_list)

        # Get terms already used in this session to avoid repeats
        current_term_names = dict(session.get("term_names", {}))
        used_term_names = set(current_term_names.values())

        # Get a quiz term, excluding already used terms
        # Use a larger batch size when we have many used terms to ensure we have options
        batch_size = max(
            20, len(used_term_names) + 10
        )  # At least 20, or more if many terms used
        terms = self.repository.get_quiz_eligible_terms(
            difficulty=difficulty,
            limit=batch_size,
            exclude_terms=list(used_term_names),
        )

        if not terms:
            # If we've exhausted all available terms, raise error
            raise ValidationError(
                f"Not enough terms available for difficulty {difficulty.value}. "
                f"All {len(used_term_names)} available terms have been used in this quiz session."
            )

        # Select random term from the filtered list
        term = random.choice(terms)

        # Format as question (with normalization and used options tracking)
        question, correct_option_id = self._format_multiple_choice(
            term, used_wrong_options
        )

        # Get wrong options used in this question (normalized)
        wrong_options_texts = [
            opt.text for opt in question.options if opt.id != correct_option_id
        ]
        new_used_wrong_options = list(used_wrong_options) + wrong_options_texts

        # Update session with new question data
        current_correct_answers = dict(session.get("correct_answers", {}))
        current_correct_answers[question.question_id] = correct_option_id
        # Create a copy of current_term_names for updating (avoid mutating original)
        current_term_names = dict(current_term_names)
        current_term_names[question.question_id] = term["slang_term"]

        self.repository.update_quiz_session(
            session_id=session_id,
            correct_answers=current_correct_answers,
            term_names=current_term_names,
            used_wrong_options=new_used_wrong_options,
        )

        logger.log_business_event(
            "quiz_question_generated",
            {
                "user_id": user_id,
                "session_id": session_id,
                "question_id": question.question_id,
                "difficulty": difficulty.value,
            },
        )

        return QuizQuestionResponse(session_id=session_id, question=question)

    @tracer.trace_method("submit_answer")
    def submit_answer(
        self, user_id: str, answer_request: QuizAnswerRequest
    ) -> QuizAnswerResponse:
        """Submit answer for one question and return immediate feedback."""
        # Load session
        session = self.repository.get_quiz_session(answer_request.session_id)
        if not session:
            raise ValidationError("Invalid or expired session")

        if session["user_id"] != user_id:
            raise ValidationError("Session does not belong to this user")

        if session.get("status") != "active":
            raise ValidationError("Session is not active")

        # Check expiration
        last_activity = datetime.fromisoformat(
            session.get("last_activity", datetime.now(timezone.utc).isoformat())
        )
        if (
            datetime.now(timezone.utc) - last_activity
        ).total_seconds() > 900:  # 15 minutes
            self.repository.update_quiz_session(
                answer_request.session_id, status="expired"
            )
            raise ValidationError("Session has expired")

        # Check if user can answer another question (free tier daily limit)
        # This check happens BEFORE processing the answer to prevent score updates after limit
        today = datetime.now(timezone.utc).date().isoformat()
        questions_today = self.user_repository.get_daily_quiz_count(user_id, today)
        user = self.user_service.get_user(user_id)
        is_premium = user is not None and user.tier != UserTier.FREE

        if not is_premium and questions_today >= self.config.free_daily_limit:
            raise UsageLimitExceededError(
                limit_type="quiz_questions",
                current_usage=questions_today,
                limit=self.config.free_daily_limit,
                message=f"Daily limit of {self.config.free_daily_limit} questions reached. Upgrade to Premium for unlimited questions!",
            )

        # Validate answer
        correct_answers = session.get("correct_answers", {})
        correct_option = correct_answers.get(answer_request.question_id)
        if not correct_option:
            raise ValidationError("Question not found in session")

        is_correct = answer_request.selected_option.lower() == correct_option.lower()

        # Calculate points using per-question time-based scoring
        points_earned = self._calculate_question_points(
            is_correct=is_correct,
            time_taken_seconds=answer_request.time_taken_seconds,
        )

        # Get term for explanation
        term_names = session.get("term_names", {})
        slang_term = term_names.get(answer_request.question_id)
        term = self.repository.get_term_by_slang(slang_term) if slang_term else None
        explanation = (
            term.get("meaning", "Term not found") if term else "Term not found"
        )
        # Normalize explanation
        explanation = self._normalize_answer_text(explanation)

        # Update session stats
        # Ensure values are proper types before arithmetic (repository should convert, but defensive)
        questions_answered = session.get("questions_answered", 0)
        correct_count = session.get("correct_count", 0)
        current_score = session.get("total_score", 0.0)

        # Convert to proper types if needed (repository should handle this, but defensive)
        if isinstance(questions_answered, (Decimal, float)):
            questions_answered = int(questions_answered)
        if isinstance(correct_count, (Decimal, float)):
            correct_count = int(correct_count)
        if isinstance(current_score, Decimal):
            current_score = float(current_score)

        new_questions_answered = questions_answered + 1
        new_correct_count = correct_count + (1 if is_correct else 0)
        new_total_score = current_score + points_earned

        self.repository.update_quiz_session(
            session_id=answer_request.session_id,
            questions_answered=new_questions_answered,
            correct_count=new_correct_count,
            total_score=new_total_score,
        )

        # Increment daily question count AFTER processing (so limit check at top prevents over-limit answers)
        self.user_repository.increment_daily_quiz_count(user_id)

        # Update quiz statistics for this term
        if slang_term:
            self.repository.update_quiz_statistics(slang_term, is_correct)

        # Calculate running stats
        accuracy = (
            float(new_correct_count) / float(new_questions_answered)
            if new_questions_answered > 0
            else 0.0
        )

        # Calculate time spent (we'll need to track this in session, but for now estimate)
        started_at = datetime.fromisoformat(
            session.get("started_at", datetime.now(timezone.utc).isoformat())
        )
        time_spent = (datetime.now(timezone.utc) - started_at).total_seconds()

        running_stats = QuizSessionProgress(
            questions_answered=new_questions_answered,
            correct_count=new_correct_count,
            total_score=new_total_score,
            accuracy=accuracy,
            time_spent_seconds=time_spent,
        )

        logger.log_business_event(
            "quiz_answer_submitted",
            {
                "user_id": user_id,
                "session_id": answer_request.session_id,
                "question_id": answer_request.question_id,
                "is_correct": is_correct,
                "points_earned": points_earned,
            },
        )

        return QuizAnswerResponse(
            is_correct=is_correct,
            points_earned=points_earned,
            explanation=explanation,
            running_stats=running_stats,
        )

    @tracer.trace_method("get_session_progress")
    def get_session_progress(
        self, user_id: str, session_id: str
    ) -> QuizSessionProgress:
        """Get current progress for a quiz session."""
        session = self.repository.get_quiz_session(session_id)
        if not session:
            raise ValidationError("Session not found")

        if session["user_id"] != user_id:
            raise ValidationError("Session does not belong to this user")

        questions_answered = session.get("questions_answered", 0)
        correct_count = session.get("correct_count", 0)
        total_score = session.get("total_score", 0.0)

        # Ensure values are proper types before arithmetic/division
        if isinstance(questions_answered, (Decimal, float)):
            questions_answered = int(questions_answered)
        if isinstance(correct_count, (Decimal, float)):
            correct_count = int(correct_count)
        if isinstance(total_score, Decimal):
            total_score = float(total_score)

        accuracy = (
            float(correct_count) / float(questions_answered)
            if questions_answered > 0
            else 0.0
        )

        started_at = datetime.fromisoformat(
            session.get("started_at", datetime.now(timezone.utc).isoformat())
        )
        time_spent = (datetime.now(timezone.utc) - started_at).total_seconds()

        return QuizSessionProgress(
            questions_answered=questions_answered,
            correct_count=correct_count,
            total_score=total_score,
            accuracy=accuracy,
            time_spent_seconds=time_spent,
        )

    @tracer.trace_method("end_session")
    def end_session(self, user_id: str, session_id: str) -> QuizResult:
        """End quiz session and return final results."""
        session = self.repository.get_quiz_session(session_id)
        if not session:
            raise ValidationError("Session not found")

        if session["user_id"] != user_id:
            raise ValidationError("Session does not belong to this user")

        if session.get("status") == "completed":
            raise ValidationError("Session already completed")

        # Calculate final stats
        # Ensure all values are proper Python types (defensive conversion from Decimal/float)

        questions_answered = session.get("questions_answered", 0)
        if isinstance(questions_answered, (Decimal, float)):
            questions_answered = int(questions_answered)
        else:
            questions_answered = int(questions_answered) if questions_answered else 0

        correct_count = session.get("correct_count", 0)
        if isinstance(correct_count, (Decimal, float)):
            correct_count = int(correct_count)
        else:
            correct_count = int(correct_count) if correct_count else 0

        total_score = session.get("total_score", 0.0)
        if isinstance(total_score, Decimal):
            total_score = float(total_score)
        else:
            total_score = float(total_score) if total_score else 0.0

        if questions_answered == 0:
            raise ValidationError("Cannot end session with no questions answered")

        # Calculate total possible (each question worth 10 points max)
        total_possible = float(questions_answered * 10.0)

        # Calculate time taken
        started_at = datetime.fromisoformat(
            session.get("started_at", datetime.now(timezone.utc).isoformat())
        )
        time_taken_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()

        # Mark session as completed
        self.repository.update_quiz_session(session_id=session_id, status="completed")

        # Save to history
        self.repository.save_quiz_result(
            user_id,
            {
                "quiz_id": session_id,
                "score": total_score,
                "total_possible": total_possible,
                "correct_count": correct_count,
                "total_questions": questions_answered,
                "time_taken_seconds": time_taken_seconds,
                "difficulty": session.get("difficulty", "beginner"),
                "challenge_type": "multiple_choice",
            },
        )

        # Round scores to whole numbers to avoid floating point precision issues
        rounded_score = int(round(total_score))
        rounded_total_possible = int(round(total_possible))

        # Generate share text
        accuracy = int((float(correct_count) / float(questions_answered)) * 100)
        share_text = f"I scored {rounded_score}/{rounded_total_possible} on the Lingible Slang Quiz! I got {correct_count}/{questions_answered} right ({accuracy}% accuracy). Can you beat me? 🔥"

        logger.log_business_event(
            "quiz_session_completed",
            {
                "user_id": user_id,
                "session_id": session_id,
                "score": rounded_score,
                "correct_count": correct_count,
                "total_questions": questions_answered,
            },
        )

        return QuizResult(
            session_id=session_id,
            score=float(
                rounded_score
            ),  # Pydantic will handle float, but explicit for clarity
            total_possible=float(rounded_total_possible),  # Pydantic will handle float
            correct_count=correct_count,  # Already int
            total_questions=questions_answered,  # Already int
            time_taken_seconds=round(time_taken_seconds, 1),
            share_text=share_text,
        )
