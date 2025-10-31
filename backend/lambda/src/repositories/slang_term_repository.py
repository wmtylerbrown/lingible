"""Repository for slang term data operations (submissions, lexicon, quiz)."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
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
        self.table_name = self.config_service._get_env_var("SLANG_TERMS_TABLE")
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
        """Update submission approval status."""
        try:
            # Find the submission item
            response = self.table.scan(
                FilterExpression="submission_id = :submission_id",
                ExpressionAttributeValues={":submission_id": submission_id},
            )

            if not response.get("Items"):
                return False

            item = response["Items"][0]

            # Update status fields
            self.table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET #status = :status, approval_type = :approval_type, reviewed_at = :timestamp, reviewed_by = :reviewer, GSI1PK = :gsi1pk",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": str(status),
                    ":approval_type": str(approval_type),
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                    ":reviewer": "system",
                    ":gsi1pk": f"STATUS#{status}",
                },
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
        """Get quiz-eligible terms by difficulty (GSI2)."""
        try:
            response = self.table.query(
                IndexName="GSI2",
                KeyConditionExpression="GSI2PK = :difficulty",
                ExpressionAttributeValues={":difficulty": f"QUIZ#{difficulty}"},
                Limit=limit * 2,  # Get extras to filter out excluded terms
                ScanIndexForward=False,  # Sort by popularity (descending)
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
        """Get terms by category (GSI3)."""
        try:
            response = self.table.query(
                IndexName="GSI3",
                KeyConditionExpression="GSI3PK = :category",
                ExpressionAttributeValues={":category": f"CATEGORY#{category}"},
                Limit=limit,
            )
            return response.get("Items", [])
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
                "score": quiz_result["score"],
                "total_possible": quiz_result["total_possible"],
                "correct_count": quiz_result["correct_count"],
                "total_questions": quiz_result["total_questions"],
                "time_taken_seconds": quiz_result["time_taken_seconds"],
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
            total_score = sum(item.get("score", 0) for item in history)
            total_possible = sum(item.get("total_possible", 100) for item in history)
            total_correct = sum(item.get("correct_count", 0) for item in history)
            total_questions = sum(item.get("total_questions", 10) for item in history)
            best_score = max(item.get("score", 0) for item in history)

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
