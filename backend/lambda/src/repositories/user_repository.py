"""User repository for user-related data operations."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from models.base import LingibleBaseModel
from models.users import User, UserTier
from models.translations import UsageLimit
from models.quiz import (
    QuizSessionRecord,
    QuizSessionStatus,
    QuizStats,
    QuizDifficulty,
)
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service
from utils.timezone_utils import (
    get_central_midnight_tomorrow,
    get_central_midnight_today,
)
from utils.exceptions import SystemError


class UserRepository:
    """Repository for user data operations."""

    QUIZ_SESSION_PREFIX = "QUIZ_SESSION#"
    QUIZ_STATS_SK = "QUIZ_STATS"
    SESSION_TTL_HOURS = 48

    def __init__(self) -> None:
        """Initialize user repository."""
        self.config_service = get_config_service()
        self.table_name = self.config_service._get_env_var("USERS_TABLE")
        self.table = aws_services.get_table(self.table_name)

    @tracer.trace_database_operation("create", "users")
    def create_user(self, user: User) -> bool:
        """Create a new user record."""
        try:
            # Convert User object to DynamoDB item format
            item = {
                "PK": f"USER#{user.user_id}",
                "SK": "PROFILE",
                **user.model_dump(mode="json"),  # Serialize the User object to dict
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            self.table.put_item(Item=item)
            # Don't log every user creation - it's a routine operation
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_user",
                    "user_id": user.user_id,
                },
            )
            raise SystemError(f"Failed to create user {user.user_id}")

    @tracer.trace_database_operation("get", "users")
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return User(**item)

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_user",
                    "user_id": user_id,
                },
            )
            return None

    @tracer.trace_database_operation("update", "users")
    def update_user(self, user: User) -> bool:
        """Update user record."""
        try:
            # Update the updated_at timestamp
            user.updated_at = datetime.now(timezone.utc)

            # Convert User object to DynamoDB item format
            item = {
                "PK": f"USER#{user.user_id}",
                "SK": "PROFILE",
                **user.model_dump(mode="json"),  # Serialize the User object to dict
                "ttl": int(
                    datetime.now(timezone.utc).timestamp() + (365 * 24 * 60 * 60)
                ),  # 1 year TTL
            }

            self.table.put_item(Item=item)
            # Don't log every user update - it's a routine operation
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_user",
                    "user_id": user.user_id,
                },
            )
            raise SystemError(f"Failed to update user {user.user_id}")

    @tracer.trace_database_operation("update", "users")
    def update_usage_limits(self, user_id: str, usage: UsageLimit) -> bool:
        """Update user usage limits."""
        try:
            item = {
                "PK": f"USER#{user_id}",
                "SK": "USAGE#LIMITS",
                "tier": usage.tier,
                "daily_used": usage.daily_used,
                "reset_daily_at": usage.reset_daily_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            # Don't log every usage limit update - it's a routine operation
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_usage_limits",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to update usage limits for user {user_id}")

    @tracer.trace_database_operation("get", "users")
    def get_usage_limits(self, user_id: str) -> Optional[UsageLimit]:
        """Get user usage limits."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "USAGE#LIMITS",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            # Ensure reset_daily_at exists, create default if missing
            reset_daily_at = item.get("reset_daily_at")
            if not reset_daily_at:
                # Create default reset date (tomorrow at midnight Central Time)
                tomorrow_start = get_central_midnight_tomorrow()
                reset_daily_at = tomorrow_start.isoformat()

            return UsageLimit(
                tier=UserTier(item["tier"]),
                daily_used=item.get("daily_used", 0),
                reset_daily_at=datetime.fromisoformat(reset_daily_at),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_usage_limits",
                    "user_id": user_id,
                },
            )
            return None

    @tracer.trace_database_operation("update", "users")
    def increment_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> bool:
        """Atomically increment usage counter and reset if needed."""
        try:
            now = datetime.now(timezone.utc)
            today_start = get_central_midnight_today()
            tomorrow_start = get_central_midnight_tomorrow()

            # First, try to increment usage (this will work if it's the same day)
            try:
                self.table.update_item(
                    Key={
                        "PK": f"USER#{user_id}",
                        "SK": "USAGE#LIMITS",
                    },
                    UpdateExpression="SET daily_used = if_not_exists(daily_used, :zero) + :one, reset_daily_at = if_not_exists(reset_daily_at, :tomorrow_start), updated_at = :updated_at, tier = if_not_exists(tier, :tier)",
                    ExpressionAttributeValues={
                        ":zero": 0,
                        ":one": 1,
                        ":today_start": today_start.isoformat(),
                        ":tomorrow_start": tomorrow_start.isoformat(),
                        ":updated_at": now.isoformat(),
                        ":tier": tier,
                    },
                    ConditionExpression="attribute_not_exists(reset_daily_at) OR reset_daily_at > :today_start",
                    ReturnValues="UPDATED_NEW",
                )

            except Exception:
                # Condition failed means it's a new day, so reset and set to 1
                self.table.update_item(
                    Key={
                        "PK": f"USER#{user_id}",
                        "SK": "USAGE#LIMITS",
                    },
                    UpdateExpression="SET daily_used = :one, reset_daily_at = :tomorrow_start, updated_at = :updated_at, tier = if_not_exists(tier, :tier)",
                    ExpressionAttributeValues={
                        ":one": 1,
                        ":tomorrow_start": tomorrow_start.isoformat(),
                        ":updated_at": now.isoformat(),
                        ":tier": tier,
                    },
                    ReturnValues="UPDATED_NEW",
                )

                # Successfully reset and incremented (new day)
                # Don't log every usage increment - it's a routine operation
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_usage",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to increment usage for user {user_id}")

    @tracer.trace_database_operation("update", "users")
    def reset_daily_usage(self, user_id: str, tier: UserTier = UserTier.FREE) -> bool:
        """Reset daily usage counter to 0."""
        try:
            now = datetime.now(timezone.utc)
            tomorrow_start = get_central_midnight_tomorrow()

            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "USAGE#LIMITS",
                },
                UpdateExpression="SET daily_used = :zero, reset_daily_at = :tomorrow_start, updated_at = :updated_at, tier = if_not_exists(tier, :tier)",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":tomorrow_start": tomorrow_start.isoformat(),
                    ":updated_at": now.isoformat(),
                    ":tier": tier,
                },
            )

            # Don't log every usage reset - it's a routine operation
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "reset_daily_usage",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to reset usage for user {user_id}")

    @tracer.trace_database_operation("delete", "users")
    def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data."""
        try:
            # Delete user profile
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                }
            )

            # Delete usage limits
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "USAGE#LIMITS",
                }
            )

            # Delete all quiz daily count items (query and delete all QUIZ_DAILY# items)
            try:
                # Query for all quiz daily items for this user
                response = self.table.query(
                    KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                    ExpressionAttributeValues={
                        ":pk": f"USER#{user_id}",
                        ":sk_prefix": "QUIZ_DAILY#",
                    },
                )
                quiz_items = response.get("Items", [])
                for item in quiz_items:
                    self.table.delete_item(
                        Key={
                            "PK": item["PK"],
                            "SK": item["SK"],
                        }
                    )
                if quiz_items:
                    logger.log_business_event(
                        "quiz_daily_count_items_deleted",
                        {
                            "user_id": user_id,
                            "deleted_count": len(quiz_items),
                        },
                    )
            except Exception as e:
                # Log but don't fail user deletion if quiz cleanup fails
                logger.log_error(
                    e,
                    {
                        "operation": "delete_quiz_daily_counts",
                        "user_id": user_id,
                    },
                )

            logger.log_business_event(
                "user_deleted",
                {
                    "user_id": user_id,
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "delete_user",
                    "user_id": user_id,
                },
            )
            raise SystemError(f"Failed to delete user {user_id}")

    @tracer.trace_database_operation("get", "daily_quiz_count")
    def get_daily_quiz_count(self, user_id: str, date: str) -> int:
        """Get number of quiz questions answered today."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{date}",
                }
            )

            if "Item" in response:
                quiz_count = response["Item"].get("quiz_count", 0)
                # Convert Decimal to int (DynamoDB returns numbers as Decimal)
                if isinstance(quiz_count, Decimal):
                    return int(quiz_count)
                return int(quiz_count) if quiz_count else 0
            return 0

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_daily_quiz_count",
                    "user_id": user_id,
                    "date": date,
                },
            )
            return 0

    @tracer.trace_database_operation("update", "daily_quiz_count")
    def increment_daily_quiz_count(self, user_id: str) -> int:
        """Increment and return daily quiz count. Creates item if needed with TTL (48h after date)."""
        try:
            today = datetime.now(timezone.utc).date()
            today_str = today.isoformat()

            # Calculate TTL: 48 hours after the date (e.g., if date is 2024-12-19, TTL = 2024-12-21 00:00 UTC)
            # Convert date string to datetime at midnight UTC, then add 48 hours
            date_obj = datetime.strptime(today_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            ttl_timestamp = int((date_obj + timedelta(hours=48)).timestamp())

            response = self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{today_str}",
                },
                UpdateExpression="ADD quiz_count :inc SET last_quiz_at = :timestamp, #ttl = :ttl",
                ExpressionAttributeNames={
                    "#ttl": "ttl",  # ttl is a reserved word in DynamoDB
                },
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                    ":ttl": ttl_timestamp,
                },
                ReturnValues="UPDATED_NEW",
            )

            quiz_count = response["Attributes"].get("quiz_count", 1)
            # Convert Decimal to int (DynamoDB returns numbers as Decimal)
            if isinstance(quiz_count, Decimal):
                return int(quiz_count)
            return int(quiz_count) if quiz_count else 1

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_daily_quiz_count",
                    "user_id": user_id,
                },
            )
            return 1

    @tracer.trace_database_operation("delete", "daily_quiz_count")
    def delete_daily_quiz_count(self, user_id: str) -> bool:
        """Delete the quiz daily count item for today."""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            self.table.delete_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{today}",
                }
            )
            return True
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "delete_daily_quiz_count",
                    "user_id": user_id,
                },
            )
            return False

    # ===== Quiz Session & Stats Methods =====

    def _quiz_session_sk(self, session_id: str) -> str:
        return f"{self.QUIZ_SESSION_PREFIX}{session_id}"

    def _session_ttl(self) -> int:
        return int(
            (
                datetime.now(timezone.utc) + timedelta(hours=self.SESSION_TTL_HOURS)
            ).timestamp()
        )

    def _deserialize_quiz_session(self, item: Dict[str, Any]) -> QuizSessionRecord:
        now = datetime.now(timezone.utc)
        raw_difficulty = item.get("difficulty")
        difficulty: QuizDifficulty
        if isinstance(raw_difficulty, QuizDifficulty):
            difficulty = raw_difficulty
        elif raw_difficulty:
            try:
                difficulty = QuizDifficulty(str(raw_difficulty))
            except ValueError:
                difficulty = QuizDifficulty.BEGINNER
        else:
            difficulty = QuizDifficulty.BEGINNER
        raw_status = item.get("status", QuizSessionStatus.ACTIVE.value)
        try:
            status = (
                raw_status
                if isinstance(raw_status, QuizSessionStatus)
                else QuizSessionStatus(str(raw_status))
            )
        except ValueError:
            status = QuizSessionStatus.ACTIVE
        return QuizSessionRecord(
            session_id=item["session_id"],
            user_id=item["user_id"],
            difficulty=difficulty,
            status=status,
            questions_answered=item.get("questions_answered", 0),
            correct_count=item.get("correct_count", 0),
            total_score=item.get("total_score", 0.0),
            correct_answers=item.get("correct_answers", {}),
            term_names=item.get("term_names", {}),
            used_wrong_options=item.get("used_wrong_options", []),
            started_at=item.get("started_at", now),
            last_activity=item.get("last_activity", now),
        )

    @tracer.trace_database_operation("create", "quiz_session")
    def create_quiz_session(
        self, user_id: str, session_id: str, difficulty: str
    ) -> bool:
        now = datetime.now(timezone.utc)
        item: Dict[str, Any] = {
            "PK": f"USER#{user_id}",
            "SK": self._quiz_session_sk(session_id),
            "session_id": session_id,
            "user_id": user_id,
            "difficulty": difficulty,
            "status": "active",
            "questions_answered": 0,
            "correct_count": 0,
            "total_score": LingibleBaseModel._to_dynamodb_value(0.0),
            "correct_answers": {},
            "term_names": {},
            "used_wrong_options": [],
            "started_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "ttl": self._session_ttl(),
        }
        self.table.put_item(Item=item)
        return True

    @tracer.trace_database_operation("get", "active_quiz_session")
    def get_active_quiz_session(self, user_id: str) -> Optional[QuizSessionRecord]:
        response = self.table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}",
                ":sk_prefix": self.QUIZ_SESSION_PREFIX,
            },
        )
        items = response.get("Items", [])
        active_sessions: List[Dict[str, Any]] = [
            item for item in items if item.get("status", "active") == "active"
        ]
        if not active_sessions:
            return None
        active_sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        session = self._deserialize_quiz_session(active_sessions[0])

        last_activity = session.last_activity
        if isinstance(last_activity, datetime):
            stale_seconds = (datetime.now(timezone.utc) - last_activity).total_seconds()
            if stale_seconds > 900:
                self.update_quiz_session(user_id, session.session_id, status="expired")
                return None
        return session

    @tracer.trace_database_operation("get", "quiz_session")
    def get_quiz_session(
        self, user_id: str, session_id: str
    ) -> Optional[QuizSessionRecord]:
        response = self.table.get_item(
            Key={
                "PK": f"USER#{user_id}",
                "SK": self._quiz_session_sk(session_id),
            }
        )
        item = response.get("Item")
        if not item:
            return None
        return self._deserialize_quiz_session(item)

    @tracer.trace_database_operation("update", "quiz_session")
    def update_quiz_session(
        self,
        user_id: str,
        session_id: str,
        questions_answered: Optional[int] = None,
        correct_count: Optional[int] = None,
        total_score: Optional[float] = None,
        correct_answers: Optional[Dict[str, str]] = None,
        term_names: Optional[Dict[str, str]] = None,
        used_wrong_options: Optional[List[str]] = None,
        status: Optional[str] = None,
        update_last_activity: bool = True,
    ) -> None:
        update_expr_parts: List[str] = []
        expr_attr_values: Dict[str, Any] = {}
        expr_attr_names: Dict[str, str] = {}

        if questions_answered is not None:
            update_expr_parts.append("questions_answered = :qa")
            expr_attr_values[":qa"] = questions_answered

        if correct_count is not None:
            update_expr_parts.append("correct_count = :cc")
            expr_attr_values[":cc"] = correct_count

        if total_score is not None:
            update_expr_parts.append("total_score = :ts")
            expr_attr_values[":ts"] = LingibleBaseModel._to_dynamodb_value(total_score)

        if correct_answers is not None:
            update_expr_parts.append("correct_answers = :ca")
            expr_attr_values[":ca"] = correct_answers

        if term_names is not None:
            update_expr_parts.append("term_names = :tn")
            expr_attr_values[":tn"] = term_names

        if used_wrong_options is not None:
            update_expr_parts.append("used_wrong_options = :uwo")
            expr_attr_values[":uwo"] = used_wrong_options

        if status is not None:
            update_expr_parts.append("#status = :status")
            expr_attr_names["#status"] = "status"
            expr_attr_values[":status"] = status

        if update_last_activity:
            update_expr_parts.append("last_activity = :la")
            expr_attr_values[":la"] = datetime.now(timezone.utc).isoformat()

        if not update_expr_parts:
            return

        update_expr_parts.append("#ttl = :ttl")
        expr_attr_names["#ttl"] = "ttl"
        expr_attr_values[":ttl"] = self._session_ttl()

        update_expr = "SET " + ", ".join(update_expr_parts)
        params: Dict[str, Any] = {
            "Key": {
                "PK": f"USER#{user_id}",
                "SK": self._quiz_session_sk(session_id),
            },
            "UpdateExpression": update_expr,
            "ExpressionAttributeValues": expr_attr_values,
        }
        if expr_attr_names:
            params["ExpressionAttributeNames"] = expr_attr_names

        self.table.update_item(**params)

    @tracer.trace_database_operation("delete", "quiz_session")
    def delete_quiz_session(self, user_id: str, session_id: str) -> bool:
        self.table.delete_item(
            Key={
                "PK": f"USER#{user_id}",
                "SK": self._quiz_session_sk(session_id),
            }
        )
        return True

    def _get_quiz_stats_item(self, user_id: str) -> Dict[str, Any]:
        response = self.table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": self.QUIZ_STATS_SK}
        )
        item = response.get("Item")
        if not item:
            return {
                "PK": f"USER#{user_id}",
                "SK": self.QUIZ_STATS_SK,
                "total_quizzes": 0,
                "total_correct": 0,
                "total_questions": 0,
                "total_score_sum": LingibleBaseModel._to_dynamodb_value(0.0),
                "total_possible_sum": LingibleBaseModel._to_dynamodb_value(0.0),
                "best_score": LingibleBaseModel._to_dynamodb_value(0.0),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        return item

    @tracer.trace_database_operation("update", "quiz_stats")
    def update_quiz_stats(
        self,
        user_id: str,
        *,
        correct_count: int,
        questions_answered: int,
        total_score: float,
        total_possible: float,
    ) -> QuizStats:
        stats_item = self._get_quiz_stats_item(user_id)
        total_quizzes = int(stats_item.get("total_quizzes", 0)) + 1
        total_correct = int(stats_item.get("total_correct", 0)) + correct_count
        total_questions = int(stats_item.get("total_questions", 0)) + questions_answered
        total_score_sum = self._to_decimal(
            stats_item.get("total_score_sum", 0)
        ) + LingibleBaseModel._to_dynamodb_value(total_score)
        total_possible_sum = self._to_decimal(
            stats_item.get("total_possible_sum", 0)
        ) + LingibleBaseModel._to_dynamodb_value(total_possible)

        new_score_pct = (
            (total_score / total_possible * 100) if total_possible > 0 else 0.0
        )
        existing_best = self._to_float(stats_item.get("best_score", 0.0))
        best_score_float = max(existing_best, new_score_pct)

        updated_item = {
            "PK": f"USER#{user_id}",
            "SK": self.QUIZ_STATS_SK,
            "total_quizzes": total_quizzes,
            "total_correct": total_correct,
            "total_questions": total_questions,
            "total_score_sum": total_score_sum,
            "total_possible_sum": total_possible_sum,
            "best_score": LingibleBaseModel._to_dynamodb_value(best_score_float),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.table.put_item(Item=updated_item)
        return QuizStats(
            total_quizzes=total_quizzes,
            total_correct=total_correct,
            total_questions=total_questions,
            average_score=(
                round((float(total_score_sum) / float(total_possible_sum)) * 100, 2)
                if total_possible_sum > 0
                else 0.0
            ),
            best_score=best_score_float,
            accuracy_rate=round(
                (
                    (float(total_correct) / float(total_questions))
                    if total_questions > 0
                    else 0.0
                ),
                3,
            ),
        )

    @tracer.trace_database_operation("get", "quiz_stats")
    def get_quiz_stats(self, user_id: str) -> QuizStats:
        stats_item = self._get_quiz_stats_item(user_id)
        total_quizzes = int(stats_item.get("total_quizzes", 0))
        total_correct = int(stats_item.get("total_correct", 0))
        total_questions = int(stats_item.get("total_questions", 0))
        total_score_sum = self._to_float(stats_item.get("total_score_sum", 0.0))
        total_possible_sum = self._to_float(stats_item.get("total_possible_sum", 0.0))

        average_score = (
            (total_score_sum / total_possible_sum) * 100
            if total_possible_sum > 0
            else 0.0
        )
        accuracy_rate = (
            (float(total_correct) / float(total_questions))
            if total_questions > 0
            else 0.0
        )

        return QuizStats(
            total_quizzes=total_quizzes,
            total_correct=total_correct,
            total_questions=total_questions,
            average_score=round(average_score, 2),
            best_score=float(stats_item.get("best_score", 0.0)),
            accuracy_rate=round(accuracy_rate, 3),
        )

    @tracer.trace_database_operation("delete", "quiz_data")
    def delete_all_quiz_data(self, user_id: str) -> None:
        response = self.table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}",
                ":sk_prefix": self.QUIZ_SESSION_PREFIX,
            },
        )
        for item in response.get("Items", []):
            self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        self.table.delete_item(Key={"PK": f"USER#{user_id}", "SK": self.QUIZ_STATS_SK})

        response_daily = self.table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}",
                ":sk_prefix": "QUIZ_DAILY#",
            },
        )
        for item in response_daily.get("Items", []):
            self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    def finalize_quiz_session(
        self,
        user_id: str,
        session_id: str,
        questions_answered: int,
        correct_count: int,
        total_score: float,
        total_possible: float,
    ) -> QuizStats:
        stats = self.update_quiz_stats(
            user_id,
            correct_count=correct_count,
            questions_answered=questions_answered,
            total_score=total_score,
            total_possible=total_possible,
        )
        self.delete_quiz_session(user_id, session_id)
        return stats

    @staticmethod
    def _to_int(value: Any) -> int:
        if isinstance(value, Decimal):
            return int(float(value))
        if isinstance(value, (int, float)):
            return int(value)
        return int(value) if value else 0

    @staticmethod
    def _to_float(value: Any) -> float:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return float(value) if value else 0.0

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        return Decimal(str(value)) if value is not None else Decimal("0")

    @tracer.trace_database_operation("update", "users")
    def increment_slang_submitted(self, user_id: str) -> bool:
        """
        Increment the slang submitted count for a user.

        Args:
            user_id: The user ID

        Returns:
            True if increment was successful
        """
        try:
            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                },
                UpdateExpression="SET slang_submitted_count = if_not_exists(slang_submitted_count, :zero) + :inc, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_slang_submitted",
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "users")
    def increment_slang_approved(self, user_id: str) -> bool:
        """
        Increment the slang approved count for a user.

        Args:
            user_id: The user ID

        Returns:
            True if increment was successful
        """
        try:
            self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": "PROFILE",
                },
                UpdateExpression="SET slang_approved_count = if_not_exists(slang_approved_count, :zero) + :inc, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_slang_approved",
                    "user_id": user_id,
                },
            )
            return False
