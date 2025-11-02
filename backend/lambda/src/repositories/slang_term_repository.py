"""Repository for slang term data operations (submissions, lexicon, quiz)."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from models.slang import (
    SlangSubmission,
    ApprovalStatus,
    SlangSubmissionStatus,
    ApprovalType,
    LLMValidationResult,
    LLMValidationEvidence,
)
from models.quiz import QuizDifficulty
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service


class SlangTermRepository:
    """Repository for all slang term operations (submissions, lexicon, quiz)."""

    def __init__(self) -> None:
        """Initialize slang term repository."""
        self.config_service = get_config_service()
        self.table_name = self.config_service._get_env_var("TERMS_TABLE")
        self.table = aws_services.get_table(self.table_name)

    def generate_submission_id(self) -> str:
        """Generate a unique submission ID."""
        return f"sub_{uuid.uuid4().hex[:16]}"

    # ===== Submission Methods (existing functionality) =====

    @tracer.trace_database_operation("create", "slang_submission")
    def create_submission(self, submission: SlangSubmission) -> bool:
        """Create a new user submission."""
        try:
            item = {
                "PK": f"TERM#{submission.slang_term.lower()}",
                "SK": f"SOURCE#user#{submission.submission_id}",
                "submission_id": submission.submission_id,
                "user_id": submission.user_id,
                "slang_term": submission.slang_term,
                "meaning": submission.meaning,
                "example_usage": submission.example_usage,
                "context": str(submission.context),
                "original_translation_id": submission.original_translation_id,
                "status": str(submission.status),
                "created_at": submission.created_at.isoformat(),
                "reviewed_at": (
                    submission.reviewed_at.isoformat()
                    if submission.reviewed_at
                    else None
                ),
                "reviewed_by": submission.reviewed_by,
                "approval_type": (
                    str(submission.approval_type) if submission.approval_type else None
                ),
                "source": "user_submission",
                "source_id": submission.submission_id,
                # GSI fields for querying by status
                "GSI1PK": f"STATUS#{submission.status}",
                "GSI1SK": submission.created_at.isoformat(),
                "GSI4PK": "SOURCE#user_submission",
                "GSI4SK": submission.slang_term,
            }

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.table.put_item(Item=item)
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_submission",
                    "submission_id": submission.submission_id,
                },
            )
            return False

    @tracer.trace_database_operation("get", "slang_submission")
    def get_submission_by_id(self, submission_id: str) -> Optional[SlangSubmission]:
        """Get a specific user submission by ID."""
        try:
            # Scan for submission by submission_id
            response = self.table.scan(
                FilterExpression="submission_id = :submission_id",
                ExpressionAttributeValues={":submission_id": submission_id},
            )

            if not response.get("Items"):
                return None

            item = response["Items"][0]
            return self._item_to_submission(item)

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_submission_by_id",
                    "submission_id": submission_id,
                },
            )
            return None

    @tracer.trace_database_operation("query", "slang_submissions")
    def get_pending_submissions(self, limit: int = 50) -> List[SlangSubmission]:
        """Get pending user submissions (GSI1)."""
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :status",
                ExpressionAttributeValues={":status": "STATUS#pending"},
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )

            submissions = []
            for item in response.get("Items", []):
                if item.get("source") == "user_submission":
                    submission = self._item_to_submission(item)
                    if submission:
                        submissions.append(submission)

            return submissions

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_pending_submissions",
                    "limit": limit,
                },
            )
            return []

    @tracer.trace_database_operation("update", "slang_submission")
    def update_validation_result(
        self, submission_id: str, user_id: str, validation_result: LLMValidationResult
    ) -> bool:
        """Update submission with LLM validation result."""
        try:
            # Find the submission item
            response = self.table.scan(
                FilterExpression="submission_id = :submission_id",
                ExpressionAttributeValues={":submission_id": submission_id},
            )

            if not response.get("Items"):
                return False

            item = response["Items"][0]

            # Update validation fields
            self.table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET llm_validation_status = :status, llm_validation_result = :result, last_used_at = :timestamp",
                ExpressionAttributeValues={
                    ":status": "validated",
                    ":result": {
                        "is_valid": validation_result.is_valid,
                        "confidence": validation_result.confidence,  # Already Decimal type
                        "evidence": [
                            {
                                "source": evidence.source,
                                "example": evidence.example,
                            }
                            for evidence in validation_result.evidence
                        ],
                        "recommended_definition": validation_result.recommended_definition,
                        "usage_score": validation_result.usage_score,
                        "validated_at": validation_result.validated_at.isoformat(),
                    },
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_validation_result",
                    "submission_id": submission_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "slang_submission")
    def update_approval_status(
        self,
        submission_id: str,
        user_id: str,
        status: SlangSubmissionStatus,
        approval_type: ApprovalType,
    ) -> bool:
        """Update submission approval status.

        When approving a submission, also sets:
        - Attestation fields (first_attested = submission date)
        - Quiz eligibility fields (difficulty, category, GSI2PK/GSI2SK)
        """
        try:
            # Find the submission item
            response = self.table.scan(
                FilterExpression="submission_id = :submission_id",
                ExpressionAttributeValues={":submission_id": submission_id},
            )

            if not response.get("Items"):
                return False

            item = response["Items"][0]

            # Base update expression for status change
            update_expression = "SET #status = :status, approval_type = :approval_type, reviewed_at = :timestamp, reviewed_by = :reviewer, GSI1PK = :gsi1pk"
            expression_values: Dict[str, Any] = {
                ":status": str(status),
                ":approval_type": str(approval_type),
                ":timestamp": datetime.now(timezone.utc).isoformat(),
                ":reviewer": "system",
                ":gsi1pk": f"STATUS#{status}",
            }

            # If approving, set attestation and quiz eligibility fields
            if status in [
                SlangSubmissionStatus.AUTO_APPROVED,
                SlangSubmissionStatus.ADMIN_APPROVED,
            ]:
                from models.quiz import QuizDifficulty, QuizCategory

                # Extract submission date for attestation (use created_at, fallback to now)
                submission_date = item.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                )
                first_attested = submission_date[:10]  # Extract YYYY-MM-DD

                # Estimate difficulty based on LLM confidence (if available)
                llm_validation_result = item.get("llm_validation_result")
                if llm_validation_result:
                    # Validation result is stored as a dict with confidence as Decimal or float
                    confidence_value = llm_validation_result.get("confidence")
                    if isinstance(confidence_value, dict):
                        # DynamoDB Decimal format
                        confidence_float = float(confidence_value.get("N", 0.85))
                    elif confidence_value is not None:
                        from decimal import Decimal

                        if isinstance(confidence_value, Decimal):
                            confidence_float = float(confidence_value)
                        else:
                            confidence_float = float(confidence_value)
                    else:
                        confidence_float = 0.85
                else:
                    # Fallback to llm_confidence_score if validation_result not available
                    llm_confidence_score = item.get("llm_confidence_score")
                    if llm_confidence_score:
                        from decimal import Decimal

                        if isinstance(llm_confidence_score, Decimal):
                            confidence_float = float(llm_confidence_score)
                        else:
                            confidence_float = float(llm_confidence_score)
                    else:
                        confidence_float = 0.85  # Default confidence

                # Estimate difficulty (same logic as migrate_lexicon)
                momentum = 1.0  # Default for user submissions
                combined_score = confidence_float * momentum
                if combined_score >= 0.9:
                    difficulty = QuizDifficulty.BEGINNER
                elif combined_score >= 0.7:
                    difficulty = QuizDifficulty.INTERMEDIATE
                else:
                    difficulty = QuizDifficulty.ADVANCED

                # Map category (user submissions default to GENERAL unless we can infer from meaning)
                category = QuizCategory.GENERAL

                # Build GSI2SK with date prioritization (same format as migration)
                # Format: {YYYYMMDD:08d}#{confidence:04d}#{term}
                reverse_date = int(first_attested.replace("-", ""))
                confidence_score = int(confidence_float * 100)
                gsi2sk = f"{reverse_date:08d}#{confidence_score:04d}#{item.get('slang_term', '')}"

                # Add attestation fields
                update_expression += ", first_attested = :first_attested, first_attested_confidence = :first_attested_confidence"
                expression_values[":first_attested"] = first_attested
                expression_values[":first_attested_confidence"] = (
                    "medium"  # Default for user submissions
                )

                # Add quiz eligibility fields
                update_expression += ", is_quiz_eligible = :is_quiz_eligible, quiz_difficulty = :quiz_difficulty, quiz_category = :quiz_category, GSI2PK = :gsi2pk, GSI2SK = :gsi2sk"
                expression_values[":is_quiz_eligible"] = True
                expression_values[":quiz_difficulty"] = str(difficulty)
                expression_values[":quiz_category"] = str(category)
                expression_values[":gsi2pk"] = f"QUIZ#{difficulty}"
                expression_values[":gsi2sk"] = gsi2sk

            # Update the item
            self.table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues=expression_values,
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_approval_status",
                    "submission_id": submission_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "slang_submission")
    def upvote_submission(self, submission_id: str, user_id: str) -> bool:
        """Add an upvote to a submission."""
        try:
            # Find the submission item
            response = self.table.scan(
                FilterExpression="submission_id = :submission_id",
                ExpressionAttributeValues={":submission_id": submission_id},
            )

            if not response.get("Items"):
                return False

            item = response["Items"][0]

            # Update upvotes
            self.table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="ADD upvotes :inc SET upvoted_by = list_append(if_not_exists(upvoted_by, :empty_list), :user_list)",
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":empty_list": [],
                    ":user_list": [user_id],
                },
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "upvote_submission",
                    "submission_id": submission_id,
                },
            )
            return False

    @tracer.trace_database_operation("query", "slang_submissions")
    def get_validated_submissions_for_voting(
        self, limit: int = 50, offset: int = 0
    ) -> List[SlangSubmission]:
        """Get validated submissions ready for community voting."""
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :status",
                ExpressionAttributeValues={":status": "STATUS#validated"},
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )

            submissions = []
            for item in response.get("Items", []):
                if item.get("source") == "user_submission":
                    submission = self._item_to_submission(item)
                    if submission:
                        submissions.append(submission)

            return submissions

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_validated_submissions_for_voting",
                    "limit": limit,
                    "offset": offset,
                },
            )
            return []

    def check_duplicate_submission(
        self, slang_term: str, user_id: str, days: int = 7
    ) -> bool:
        """Check if user has already submitted this term recently."""
        try:
            # Check for existing submissions by this user for this term
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

            response = self.table.query(
                IndexName="GSI4",
                KeyConditionExpression="GSI4PK = :source AND GSI4SK = :term",
                FilterExpression="user_id = :user_id AND created_at >= :cutoff",
                ExpressionAttributeValues={
                    ":source": "SOURCE#user_submission",
                    ":term": slang_term.lower(),
                    ":user_id": user_id,
                    ":cutoff": cutoff_date.isoformat(),
                },
            )

            return len(response.get("Items", [])) > 0

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "check_duplicate_submission",
                    "slang_term": slang_term,
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("scan", "slang_submissions")
    def get_user_submissions(
        self, user_id: str, limit: int = 20
    ) -> List[SlangSubmission]:
        """Get all submissions by a specific user."""
        try:
            response = self.table.scan(
                FilterExpression="user_id = :user_id AND source = :source",
                ExpressionAttributeValues={
                    ":user_id": user_id,
                    ":source": "user_submission",
                },
                Limit=limit * 2,  # Get extras to ensure we have enough after filtering
            )

            submissions = []
            for item in response.get("Items", []):
                submission = self._item_to_submission(item)
                if submission:
                    submissions.append(submission)

            # Sort by created_at descending
            submissions.sort(key=lambda x: x.created_at, reverse=True)
            return submissions[:limit]

        except Exception as e:
            logger.log_error(
                e, {"operation": "get_user_submissions", "user_id": user_id}
            )
            return []

    # ===== Lexicon Methods (NEW) =====

    @tracer.trace_database_operation("create", "lexicon_term")
    def create_lexicon_term(self, term_data: dict) -> bool:
        """Create a lexicon term from imported data."""
        try:
            self.table.put_item(Item=term_data)
            return True
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_lexicon_term",
                    "slang_term": term_data.get("slang_term"),
                },
            )
            return False

    @tracer.trace_database_operation("query", "lexicon_terms")
    def get_all_lexicon_terms(self) -> List[dict]:
        """Get all lexicon terms (GSI4)."""
        try:
            response = self.table.query(
                IndexName="GSI4",
                KeyConditionExpression="GSI4PK = :source",
                ExpressionAttributeValues={":source": "SOURCE#lexicon"},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.log_error(e, {"operation": "get_all_lexicon_terms"})
            return []

    @tracer.trace_database_operation("get", "slang_term")
    def get_term_by_slang(self, slang_term: str) -> Optional[dict]:
        """Get canonical term (prefers lexicon over user submissions)."""
        try:
            # Query for all records with this term
            response = self.table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"TERM#{slang_term.lower()}"},
            )

            if not response.get("Items"):
                return None

            # Prefer lexicon over user submissions
            items = response["Items"]
            for item in items:
                if item.get("source") == "lexicon":
                    return item

            # Fall back to first item (user submission)
            return items[0] if items else None

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_term_by_slang",
                    "slang_term": slang_term,
                },
            )
            return None

    # ===== Quiz Methods (NEW) =====

    @tracer.trace_database_operation("query", "quiz_terms")
    def get_quiz_eligible_terms(
        self, difficulty: QuizDifficulty, limit: int = 10, exclude_terms: List[str] = []
    ) -> List[dict]:
        """Get quiz-eligible terms by difficulty (GSI2).

        Terms are sorted by:
        1. first_attested date (newest first)
        2. confidence score (higher first, within same date)
        3. term name (lexicographic, within same date+confidence)

        This prioritizes newer slang terms while maintaining popularity-based
        selection within the same time period.
        """
        try:
            response = self.table.query(
                IndexName="GSI2",
                KeyConditionExpression="GSI2PK = :difficulty",
                ExpressionAttributeValues={":difficulty": f"QUIZ#{difficulty}"},
                Limit=limit * 2,  # Get extras to filter out excluded terms
                ScanIndexForward=False,  # Descending: newer dates + higher confidence first
            )

            items = response.get("Items", [])

            # Filter out excluded terms and ensure quiz eligibility
            eligible_items = [
                item
                for item in items
                if (
                    item.get("is_quiz_eligible", False)
                    and item.get("slang_term") not in exclude_terms
                )
            ]

            return eligible_items[:limit]

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_quiz_eligible_terms",
                    "difficulty": difficulty,
                    "limit": limit,
                },
            )
            return []

    @tracer.trace_database_operation("query", "category_terms")
    def get_terms_by_category(self, category: str, limit: int = 50) -> List[dict]:
        """Get terms by category (GSI3).

        Note: GSI3 uses KEYS_ONLY projection, so we fetch full items via GetItem
        for each result if meaning/slang_term fields are needed.
        """
        try:
            response = self.table.query(
                IndexName="GSI3",
                KeyConditionExpression="GSI3PK = :category",
                ExpressionAttributeValues={":category": f"CATEGORY#{category}"},
                Limit=limit,
            )
            items = response.get("Items", [])

            # GSI3 is KEYS_ONLY projection, so always fetch full items
            # For fallback wrong answer generation, we need meaning and slang_term
            full_items = []
            for item in items:
                # KEYS_ONLY only returns PK and SK, so always fetch full item
                full_item = self.table.get_item(
                    Key={
                        "PK": item["PK"],
                        "SK": item["SK"],
                    }
                ).get("Item")
                if full_item:
                    full_items.append(full_item)

            return full_items
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_terms_by_category",
                    "category": category,
                    "limit": limit,
                },
            )
            return []

    @tracer.trace_database_operation("update", "quiz_statistics")
    def update_quiz_statistics(self, term: str, was_correct: bool) -> None:
        """Update quiz performance statistics."""
        try:
            # Find the term item
            response = self.table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"TERM#{term.lower()}"},
            )

            if not response.get("Items"):
                return

            # Update stats for the first item found
            item = response["Items"][0]

            # Calculate new accuracy rate
            current_times = item.get("times_in_quiz", 0)
            # Convert to Decimal if it's a number (from DynamoDB it might be Decimal already)
            current_accuracy_raw = item.get("quiz_accuracy_rate", Decimal("0.5"))
            current_accuracy = (
                current_accuracy_raw
                if isinstance(current_accuracy_raw, Decimal)
                else Decimal(str(current_accuracy_raw))
            )

            new_times = current_times + 1
            if current_times == 0:
                new_accuracy = Decimal("1.0") if was_correct else Decimal("0.0")
            else:
                total_correct = current_accuracy * current_times
                if was_correct:
                    total_correct += 1
                # Convert division result to Decimal
                new_accuracy = Decimal(str(total_correct / new_times))

            self.table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET times_in_quiz = :times, quiz_accuracy_rate = :accuracy, last_used_at = :timestamp",
                ExpressionAttributeValues={
                    ":times": new_times,
                    ":accuracy": new_accuracy,  # Already Decimal type
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_quiz_statistics",
                    "term": term,
                    "was_correct": was_correct,
                },
            )

    # ===== Quiz History Methods (NEW) =====

    @tracer.trace_database_operation("create", "quiz_result")
    def save_quiz_result(self, user_id: str, quiz_result: dict) -> bool:
        """Save completed quiz to history."""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            quiz_id = quiz_result["quiz_id"]

            item = {
                "PK": f"USER#{user_id}",
                "SK": f"QUIZ#{today}#{quiz_id}",
                "user_id": user_id,
                "quiz_id": quiz_id,
                "challenge_type": quiz_result.get("challenge_type", "multiple_choice"),
                "difficulty": quiz_result.get("difficulty", "beginner"),
                # Convert float to Decimal for DynamoDB (repository boundary conversion)
                "score": Decimal(str(quiz_result["score"])),
                "total_possible": Decimal(str(quiz_result["total_possible"])),
                "correct_count": quiz_result["correct_count"],
                "total_questions": quiz_result["total_questions"],
                "time_taken_seconds": Decimal(str(quiz_result["time_taken_seconds"])),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                # GSI5 for user quiz history queries
                "GSI5PK": f"QUIZHISTORY#{user_id}",
                "GSI5SK": datetime.now(timezone.utc).isoformat(),
            }

            self.table.put_item(Item=item)
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "save_quiz_result",
                    "user_id": user_id,
                    "quiz_id": quiz_result.get("quiz_id"),
                },
            )
            return False

    @tracer.trace_database_operation("get", "daily_quiz_count")
    def get_daily_quiz_count(self, user_id: str, date: str) -> int:
        """Get number of quizzes taken today."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{date}",
                }
            )

            if "Item" in response:
                return response["Item"].get("quiz_count", 0)
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
        """Increment and return daily quiz count."""
        try:
            today = datetime.now(timezone.utc).date().isoformat()

            response = self.table.update_item(
                Key={
                    "PK": f"USER#{user_id}",
                    "SK": f"QUIZ_DAILY#{today}",
                },
                UpdateExpression="ADD quiz_count :inc SET last_quiz_at = :timestamp",
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                },
                ReturnValues="UPDATED_NEW",
            )

            return response["Attributes"].get("quiz_count", 1)

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "increment_daily_quiz_count",
                    "user_id": user_id,
                },
            )
            return 1

    @tracer.trace_database_operation("query", "quiz_history")
    def get_user_quiz_history(self, user_id: str, limit: int = 20) -> List[dict]:
        """Get user's quiz history (GSI5)."""
        try:
            response = self.table.query(
                IndexName="GSI5",
                KeyConditionExpression="GSI5PK = :user_quiz_history",
                ExpressionAttributeValues={
                    ":user_quiz_history": f"QUIZHISTORY#{user_id}"
                },
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )
            return response.get("Items", [])
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_user_quiz_history",
                    "user_id": user_id,
                    "limit": limit,
                },
            )
            return []

    @tracer.trace_database_operation("query", "quiz_stats")
    def get_user_quiz_stats(self, user_id: str) -> dict:
        """Calculate aggregate stats for user."""
        try:
            history = self.get_user_quiz_history(user_id, limit=1000)  # Get all history

            if not history:
                return {
                    "total_quizzes": 0,
                    "average_score": 0.0,
                    "best_score": 0,
                    "total_correct": 0,
                    "total_questions": 0,
                    "accuracy_rate": 0.0,
                }

            total_quizzes = len(history)

            # Convert Decimal to float for service layer (DynamoDB returns Decimal)
            def get_score(item):
                score = item.get("score", 0)
                return float(score) if isinstance(score, Decimal) else score

            def get_total_possible(item):
                tp = item.get("total_possible", 100)
                return float(tp) if isinstance(tp, Decimal) else tp

            total_score = sum(get_score(item) for item in history)
            total_possible = sum(get_total_possible(item) for item in history)
            total_correct = sum(item.get("correct_count", 0) for item in history)
            total_questions = sum(item.get("total_questions", 10) for item in history)
            best_score = max(get_score(item) for item in history)

            average_score = (
                (total_score / total_possible * 100) if total_possible > 0 else 0.0
            )
            accuracy_rate = (
                (total_correct / total_questions) if total_questions > 0 else 0.0
            )

            return {
                "total_quizzes": total_quizzes,
                "average_score": round(average_score, 2),
                "best_score": best_score,
                "total_correct": total_correct,
                "total_questions": total_questions,
                "accuracy_rate": round(accuracy_rate, 3),
            }

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_user_quiz_stats",
                    "user_id": user_id,
                },
            )
            return {
                "total_quizzes": 0,
                "average_score": 0.0,
                "best_score": 0,
                "total_correct": 0,
                "total_questions": 0,
                "accuracy_rate": 0.0,
            }

    # ===== Quiz Session Methods (NEW) =====

    @tracer.trace_database_operation("create", "quiz_session")
    def create_quiz_session(
        self,
        session_id: str,
        user_id: str,
        difficulty: str,
    ) -> bool:
        """Create a new quiz session."""
        try:
            now = datetime.now(timezone.utc)
            expires_at = int((now + timedelta(hours=24)).timestamp())

            item = {
                "PK": f"USER#{user_id}",
                "SK": f"SESSION#{session_id}",
                "session_id": session_id,
                "user_id": user_id,
                "difficulty": difficulty,
                "questions_answered": 0,
                "correct_count": 0,
                "total_score": Decimal("0.0"),
                "started_at": now.isoformat(),
                "last_activity": now.isoformat(),
                "status": "active",
                "correct_answers": {},
                "term_names": {},
                "used_wrong_options": [],
                "expires_at": expires_at,  # TTL for auto-cleanup
                # GSI6 for session lookup by session_id
                "GSI6PK": f"SESSION#{session_id}",
                "GSI6SK": now.isoformat(),
            }

            self.table.put_item(Item=item)
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "create_quiz_session",
                    "session_id": session_id,
                    "user_id": user_id,
                },
            )
            return False

    @tracer.trace_database_operation("get", "quiz_session")
    def get_quiz_session(self, session_id: str) -> Optional[dict]:
        """Get quiz session by session_id.

        Returns dict with Decimal values converted to float for service layer compatibility.
        """
        try:
            # Use GSI6 to lookup by session_id
            response = self.table.query(
                IndexName="GSI6",
                KeyConditionExpression="GSI6PK = :session_pk",
                ExpressionAttributeValues={":session_pk": f"SESSION#{session_id}"},
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                session = items[0]
                # Convert Decimal to Python types for service layer compatibility
                if "total_score" in session and isinstance(
                    session["total_score"], Decimal
                ):
                    session["total_score"] = float(session["total_score"])
                if "questions_answered" in session and isinstance(
                    session["questions_answered"], Decimal
                ):
                    session["questions_answered"] = int(session["questions_answered"])
                if "correct_count" in session and isinstance(
                    session["correct_count"], Decimal
                ):
                    session["correct_count"] = int(session["correct_count"])
                return session
            return None

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "get_quiz_session", "session_id": session_id},
            )
            return None

    @tracer.trace_database_operation("get", "active_quiz_session")
    def get_active_quiz_session(self, user_id: str) -> Optional[dict]:
        """Get active quiz session for a user."""
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                FilterExpression="#status = :active",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":pk": f"USER#{user_id}",
                    ":sk_prefix": "SESSION#",
                    ":active": "active",
                },
            )

            items = response.get("Items", [])
            # Get most recent active session
            if items:
                # Sort by last_activity descending
                items.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
                session = items[0]

                # Convert Decimal to Python types for service layer compatibility
                if "total_score" in session and isinstance(
                    session["total_score"], Decimal
                ):
                    session["total_score"] = float(session["total_score"])
                if "questions_answered" in session and isinstance(
                    session["questions_answered"], Decimal
                ):
                    session["questions_answered"] = int(session["questions_answered"])
                if "correct_count" in session and isinstance(
                    session["correct_count"], Decimal
                ):
                    session["correct_count"] = int(session["correct_count"])

                # Check if expired (> 15 minutes)
                last_activity = datetime.fromisoformat(
                    session.get("last_activity", datetime.now(timezone.utc).isoformat())
                )
                if (
                    datetime.now(timezone.utc) - last_activity
                ).total_seconds() > 900:  # 15 minutes
                    # Mark as expired
                    self.update_quiz_session(
                        session_id=session["session_id"], status="expired"
                    )
                    return None

                return session
            return None

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "get_active_quiz_session", "user_id": user_id},
            )
            return None

    @tracer.trace_database_operation("update", "quiz_session")
    def update_quiz_session(
        self,
        session_id: str,
        questions_answered: Optional[int] = None,
        correct_count: Optional[int] = None,
        total_score: Optional[float] = None,
        correct_answers: Optional[Dict[str, str]] = None,
        term_names: Optional[Dict[str, str]] = None,
        used_wrong_options: Optional[List[str]] = None,
        status: Optional[str] = None,
        update_last_activity: bool = True,
    ) -> bool:
        """Update quiz session."""
        try:
            now = datetime.now(timezone.utc)

            # Build update expression
            update_expr_parts = []
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
                # Convert float to Decimal for DynamoDB (always convert at repository boundary)
                expr_attr_values[":ts"] = Decimal(str(total_score))

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
                expr_attr_values[":la"] = now.isoformat()

            if not update_expr_parts:
                return True  # Nothing to update

            # Get session to find PK/SK
            session = self.get_quiz_session(session_id)
            if not session:
                return False

            update_expr = "SET " + ", ".join(update_expr_parts)

            update_params = {
                "Key": {"PK": session["PK"], "SK": session["SK"]},
                "UpdateExpression": update_expr,
                "ExpressionAttributeValues": expr_attr_values,
            }

            if expr_attr_names:
                update_params["ExpressionAttributeNames"] = expr_attr_names

            self.table.update_item(**update_params)
            return True

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "update_quiz_session", "session_id": session_id},
            )
            return False

    @tracer.trace_database_operation("delete", "quiz_session")
    def delete_quiz_session(self, session_id: str) -> bool:
        """Delete quiz session."""
        try:
            session = self.get_quiz_session(session_id)
            if not session:
                return False

            self.table.delete_item(Key={"PK": session["PK"], "SK": session["SK"]})
            return True

        except Exception as e:
            logger.log_error(
                e,
                {"operation": "delete_quiz_session", "session_id": session_id},
            )
            return False

    # ===== Wrong Answer Pool Methods =====

    @tracer.trace_database_operation("get", "wrong_answer_pool")
    def get_wrong_answer_pool(self, category: str) -> Optional[List[str]]:
        """Get wrong answer pool for a category."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"QUIZPOOL#{category}",
                    "SK": f"CATEGORY#{category}",
                }
            )
            item = response.get("Item")
            if item:
                return item.get("pool", [])
            return None
        except Exception as e:
            logger.log_error(
                e,
                {"operation": "get_wrong_answer_pool", "category": category},
            )
            return None

    @tracer.trace_database_operation("create", "wrong_answer_pool")
    def create_wrong_answer_pool(self, category: str, pool: List[str]) -> bool:
        """Create or update wrong answer pool for a category."""
        try:
            item = {
                "PK": f"QUIZPOOL#{category}",
                "SK": f"CATEGORY#{category}",
                "category": category,
                "pool": pool,
                "pool_size": len(pool),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.table.put_item(Item=item)
            logger.log_debug(
                "Wrong answer pool created",
                {"category": category, "pool_size": len(pool)},
            )
            return True
        except Exception as e:
            logger.log_error(
                e,
                {"operation": "create_wrong_answer_pool", "category": category},
            )
            return False

    # ===== Export Methods (NEW) =====

    @tracer.trace_database_operation("scan", "approved_terms")
    def get_all_approved_terms(self) -> List[dict]:
        """Get all approved terms for S3 export."""
        try:
            # Scan for all approved terms (both lexicon and user submissions)
            response = self.table.scan(
                FilterExpression="attribute_exists(#status) AND #status = :approved",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":approved": "approved"},
            )

            return response.get("Items", [])

        except Exception as e:
            logger.log_error(e, {"operation": "get_all_approved_terms"})
            return []

    @tracer.trace_database_operation("update", "export_tracking")
    def mark_exported(self, term: str, source: str) -> None:
        """Mark term as exported to S3."""
        try:
            # Find the term item
            response = self.table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"TERM#{term.lower()}"},
            )

            if not response.get("Items"):
                return

            # Update export tracking for the first item found
            item = response["Items"][0]

            self.table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET exported_to_s3 = :exported, last_exported_at = :timestamp",
                ExpressionAttributeValues={
                    ":exported": True,
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "mark_exported",
                    "term": term,
                    "source": source,
                },
            )

    # ===== Helper Methods =====

    def _item_to_submission(self, item: dict) -> Optional[SlangSubmission]:
        """Convert DynamoDB item to SlangSubmission model."""
        try:
            # Parse validation result if present
            llm_validation_result = None
            if item.get("llm_validation_result"):
                validation_data = item["llm_validation_result"]
                evidence = []
                for evidence_item in validation_data.get("evidence", []):
                    evidence.append(
                        LLMValidationEvidence(
                            source=evidence_item["source"],
                            example=evidence_item["example"],
                        )
                    )

                llm_validation_result = LLMValidationResult(
                    is_valid=validation_data["is_valid"],
                    confidence=Decimal(str(validation_data["confidence"])),
                    evidence=evidence,
                    recommended_definition=validation_data.get(
                        "recommended_definition"
                    ),
                    usage_score=validation_data.get("usage_score", 0),
                    validated_at=datetime.fromisoformat(
                        validation_data["validated_at"].replace("Z", "+00:00")
                    ),
                )

            return SlangSubmission(
                submission_id=item["submission_id"],
                user_id=item["user_id"],
                slang_term=item["slang_term"],
                meaning=item["meaning"],
                example_usage=item.get("example_usage"),
                context=item.get("context", "manual"),
                original_translation_id=item.get("original_translation_id"),
                status=ApprovalStatus(item["status"]),
                created_at=datetime.fromisoformat(
                    item["created_at"].replace("Z", "+00:00")
                ),
                reviewed_at=(
                    datetime.fromisoformat(item["reviewed_at"].replace("Z", "+00:00"))
                    if item.get("reviewed_at")
                    else None
                ),
                reviewed_by=item.get("reviewed_by"),
                approval_type=(
                    ApprovalType(item["approval_type"])
                    if item.get("approval_type")
                    else None
                ),
                llm_validation_status=SlangSubmissionStatus(
                    item.get("llm_validation_status", "pending")
                ),
                llm_confidence_score=(
                    Decimal(str(item["llm_confidence_score"]))
                    if item.get("llm_confidence_score") is not None
                    else (
                        Decimal(str(llm_validation_result.confidence))
                        if llm_validation_result and llm_validation_result.confidence
                        else None
                    )
                ),
                llm_validation_result=llm_validation_result,
                approved_by=item.get("approved_by"),
                upvotes=item.get("upvotes", 0),
                upvoted_by=item.get("upvoted_by", []),
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "_item_to_submission",
                    "submission_id": item.get("submission_id"),
                },
            )
            return None
