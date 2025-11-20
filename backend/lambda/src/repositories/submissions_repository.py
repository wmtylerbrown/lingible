"""Repository for slang submissions stored in the SubmissionsTable."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from models.quiz import QuizCategory, QuizDifficulty
from models.slang import (
    ApprovalStatus,
    ApprovalType,
    LLMValidationEvidence,
    LLMValidationResult,
    SlangSubmission,
    SlangSubmissionStatus,
    SubmissionContext,
)
from utils.aws_services import aws_services
from utils.config import get_config_service
from utils.smart_logger import logger
from utils.tracing import tracer


class SubmissionsRepository:
    """Repository for user-submitted slang terms (moderation workflow)."""

    def __init__(self) -> None:
        config_service = get_config_service()
        self.table_name = config_service._get_env_var("SUBMISSIONS_TABLE")
        self.table = aws_services.get_table(self.table_name)

    def generate_submission_id(self) -> str:
        """Generate a unique submission ID."""
        return f"sub_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _submission_pk(term: str) -> str:
        return f"TERM#{term.lower()}"

    @staticmethod
    def _submission_sk(submission_id: str) -> str:
        return f"SUBMISSION#{submission_id}"

    @tracer.trace_database_operation("create", "submissions")
    def create_submission(self, submission: SlangSubmission) -> bool:
        """Persist a new user submission."""
        try:
            item = {
                "PK": self._submission_pk(submission.slang_term),
                "SK": self._submission_sk(submission.submission_id),
                "submission_id": submission.submission_id,
                "user_id": submission.user_id,
                "slang_term": submission.slang_term,
                "meaning": submission.meaning,
                "example_usage": submission.example_usage,
                "context": submission.context.value,
                "original_translation_id": submission.original_translation_id,
                "status": submission.status.value,
                "status_created_at": submission.created_at.isoformat(),
                "user_created_at": submission.created_at.isoformat(),
                "created_at": submission.created_at.isoformat(),
                "reviewed_at": (
                    submission.reviewed_at.isoformat()
                    if submission.reviewed_at
                    else None
                ),
                "reviewed_by": submission.reviewed_by,
                "approval_type": (
                    submission.approval_type.value if submission.approval_type else None
                ),
                "llm_validation_status": (
                    submission.llm_validation_status.value
                    if submission.llm_validation_status
                    else SlangSubmissionStatus.PENDING_VALIDATION.value
                ),
                "llm_confidence_score": submission.llm_confidence_score,
                "llm_validation_result": self._serialize_llm_result(
                    submission.llm_validation_result
                ),
                "approval_status": submission.status.value,
                "source": "user_submission",
                "upvotes": submission.upvotes,
                "upvoted_by": submission.upvoted_by,
            }

            # Remove None values
            payload = {k: v for k, v in item.items() if v is not None}
            self.table.put_item(Item=payload)
            return True

        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "create_submission",
                    "submission_id": submission.submission_id,
                },
            )
            return False

    def _serialize_llm_result(
        self, result: Optional[LLMValidationResult]
    ) -> Optional[Dict[str, Any]]:
        if result is None:
            return None
        return {
            "is_valid": result.is_valid,
            "confidence": result.confidence,
            "recommended_definition": result.recommended_definition,
            "usage_score": result.usage_score,
            "validated_at": (
                result.validated_at.isoformat() if result.validated_at else None
            ),
            "evidence": [
                {"source": evidence.source, "example": evidence.example}
                for evidence in result.evidence
            ],
        }

    def _item_to_submission(self, item: Dict[str, Any]) -> Optional[SlangSubmission]:
        try:
            created_at = datetime.fromisoformat(item["created_at"])
            reviewed_at = (
                datetime.fromisoformat(item["reviewed_at"])
                if item.get("reviewed_at")
                else None
            )
            llm_status = item.get("llm_validation_status")
            llm_status_enum = (
                SlangSubmissionStatus(llm_status)
                if llm_status
                else SlangSubmissionStatus.PENDING_VALIDATION
            )
            llm_result = self._deserialize_llm_result(item.get("llm_validation_result"))
            upvotes_value = item.get("upvotes", 0)
            if isinstance(upvotes_value, Decimal):
                upvotes_value = int(upvotes_value)

            submission = SlangSubmission(
                submission_id=item["submission_id"],
                user_id=item["user_id"],
                slang_term=item["slang_term"],
                meaning=item.get("meaning", ""),
                example_usage=item.get("example_usage"),
                context=SubmissionContext(
                    item.get("context", SubmissionContext.MANUAL)
                ),
                original_translation_id=item.get("original_translation_id"),
                status=ApprovalStatus(item.get("status", ApprovalStatus.PENDING)),
                created_at=created_at,
                reviewed_at=reviewed_at,
                reviewed_by=item.get("reviewed_by"),
                llm_validation_status=llm_status_enum,
                llm_confidence_score=self._to_decimal(item.get("llm_confidence_score")),
                llm_validation_result=llm_result,
                approval_type=(
                    ApprovalType(item["approval_type"])
                    if item.get("approval_type")
                    else None
                ),
                approved_by=item.get("approved_by"),
                upvotes=upvotes_value,
                upvoted_by=item.get("upvoted_by", []),
            )
            return submission
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "_item_to_submission",
                    "submission_id": item.get("submission_id"),
                },
            )
            return None

    def _deserialize_llm_result(
        self, raw: Optional[Dict[str, Any]]
    ) -> Optional[LLMValidationResult]:
        if not raw:
            return None
        evidence = [
            LLMValidationEvidence(source=e["source"], example=e["example"])
            for e in raw.get("evidence", [])
            if e.get("source") and e.get("example")
        ]
        validated_at = raw.get("validated_at")
        validated_dt = (
            datetime.fromisoformat(validated_at)
            if validated_at
            else datetime.now(timezone.utc)
        )
        confidence_value = self._to_decimal(raw.get("confidence", Decimal("0.8")))
        return LLMValidationResult(
            is_valid=bool(raw.get("is_valid", True)),
            confidence=(
                confidence_value if confidence_value is not None else Decimal("0.8")
            ),
            recommended_definition=raw.get("recommended_definition"),
            usage_score=int(raw.get("usage_score", 0)),
            validated_at=validated_dt,
            evidence=evidence,
        )

    @staticmethod
    def _to_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _query_status_index(
        self, status: ApprovalStatus | SlangSubmissionStatus, limit: int
    ) -> List[SlangSubmission]:
        try:
            status_value = status.value if hasattr(status, "value") else str(status)
            response = self.table.query(
                IndexName="SubmissionsStatusIndex",
                KeyConditionExpression="status = :status",
                ExpressionAttributeValues={":status": status_value},
                Limit=limit,
                ScanIndexForward=False,
            )
            return self._items_to_submissions(response.get("Items", []))
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "_query_status_index",
                    "status": status_value,
                },
            )
            return []

    def _items_to_submissions(
        self, items: List[Dict[str, Any]]
    ) -> List[SlangSubmission]:
        submissions: List[SlangSubmission] = []
        for item in items:
            source_item = item
            if "created_at" not in item and "PK" in item and "SK" in item:
                source_item = (
                    self.table.get_item(Key={"PK": item["PK"], "SK": item["SK"]}).get(
                        "Item"
                    )
                    or item
                )
            submission = self._item_to_submission(source_item)
            if submission:
                submissions.append(submission)
        return submissions

    @tracer.trace_database_operation("query", "submissions")
    def get_submissions_by_status(
        self, status: ApprovalStatus, limit: int = 50
    ) -> List[SlangSubmission]:
        return self._query_status_index(status, limit)

    @tracer.trace_database_operation("query", "submissions")
    def get_pending_submissions(self, limit: int = 50) -> List[SlangSubmission]:
        return self.get_submissions_by_status(ApprovalStatus.PENDING, limit)

    @tracer.trace_database_operation("query", "submissions")
    def get_validated_submissions_for_voting(
        self, limit: int = 50
    ) -> List[SlangSubmission]:
        return self.get_by_validation_status(SlangSubmissionStatus.VALIDATED, limit)

    @tracer.trace_database_operation("get", "submissions")
    def get_submission_by_id(self, submission_id: str) -> Optional[SlangSubmission]:
        item = self._get_item_by_submission_id(submission_id)
        return self._item_to_submission(item) if item else None

    def _get_item_by_submission_id(
        self, submission_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            response = self.table.query(
                IndexName="SubmissionsByIdIndex",
                KeyConditionExpression="submission_id = :submission_id",
                ExpressionAttributeValues={":submission_id": submission_id},
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "_get_item_by_submission_id",
                    "submission_id": submission_id,
                },
            )
            return None

    def _get_key_for_submission(self, submission_id: str) -> Optional[Dict[str, str]]:
        item = self._get_item_by_submission_id(submission_id)
        if not item:
            return None
        return {"PK": item["PK"], "SK": item["SK"]}

    @tracer.trace_database_operation("query", "submissions")
    def get_user_submissions(
        self, user_id: str, limit: int = 20
    ) -> List[SlangSubmission]:
        try:
            response = self.table.query(
                IndexName="SubmissionsByUserIndex",
                KeyConditionExpression="user_id = :user_id",
                ExpressionAttributeValues={":user_id": user_id},
                Limit=limit * 2,
                ScanIndexForward=False,
            )

            submissions: List[SlangSubmission] = []
            for item in response.get("Items", []):
                full_item = self.table.get_item(
                    Key={"PK": item["PK"], "SK": item["SK"]}
                ).get("Item")
                if full_item:
                    submission = self._item_to_submission(full_item)
                    if submission:
                        submissions.append(submission)

            submissions.sort(key=lambda sub: sub.created_at, reverse=True)
            return submissions[:limit]
        except Exception as exc:
            logger.log_error(
                exc,
                {"operation": "get_user_submissions", "user_id": user_id},
            )
            return []

    @tracer.trace_database_operation("update", "submissions")
    def update_validation_result(
        self, submission_id: str, user_id: str, validation_result: LLMValidationResult
    ) -> bool:
        try:
            key = self._get_key_for_submission(submission_id)
            if not key:
                return False

            payload = self._serialize_llm_result(validation_result)
            if payload is None:
                return False

            self.table.update_item(
                Key=key,
                UpdateExpression=(
                    "SET llm_validation_status = :status, "
                    "llm_validation_result = :result, "
                    "last_used_at = :timestamp"
                ),
                ExpressionAttributeValues={
                    ":status": SlangSubmissionStatus.VALIDATED.value,
                    ":result": payload,
                    ":timestamp": self._now_iso(),
                },
            )
            return True
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "update_validation_result",
                    "submission_id": submission_id,
                },
            )
            return False

    @tracer.trace_database_operation("update", "submissions")
    def update_approval_status(
        self,
        submission_id: str,
        user_id: str,
        workflow_status: SlangSubmissionStatus,
        approval_type: ApprovalType,
    ) -> bool:
        try:
            item = self._get_item_by_submission_id(submission_id)
            if not item:
                return False

            key = {"PK": item["PK"], "SK": item["SK"]}
            timestamp = self._now_iso()
            update_expression = (
                "SET #status = :status, "
                "status_created_at = :status_created_at, "
                "approval_type = :approval_type, "
                "reviewed_at = :reviewed_at, "
                "reviewed_by = :reviewed_by, "
                "llm_validation_status = :workflow_status"
            )

            expression_values: Dict[str, Any] = {
                ":status": (
                    ApprovalStatus.APPROVED.value
                    if workflow_status
                    in (
                        SlangSubmissionStatus.AUTO_APPROVED,
                        SlangSubmissionStatus.ADMIN_APPROVED,
                    )
                    else (
                        ApprovalStatus.REJECTED.value
                        if workflow_status == SlangSubmissionStatus.REJECTED
                        else ApprovalStatus.PENDING.value
                    )
                ),
                ":status_created_at": timestamp,
                ":approval_type": approval_type.value,
                ":reviewed_at": timestamp,
                ":reviewed_by": "system",
                ":workflow_status": workflow_status.value,
            }

            # If approval, set quiz metadata approximations
            if workflow_status in (
                SlangSubmissionStatus.AUTO_APPROVED,
                SlangSubmissionStatus.ADMIN_APPROVED,
            ):
                created_at_value = item.get("created_at", timestamp)[:10]
                expression_values.update(
                    {
                        ":first_attested": created_at_value,
                        ":first_attested_confidence": "medium",
                        ":quiz_category": QuizCategory.GENERAL.value,
                        ":quiz_difficulty": self._estimate_difficulty(item).value,
                        ":is_quiz_eligible": True,
                    }
                )
                update_expression += (
                    ", first_attested = :first_attested, "
                    "first_attested_confidence = :first_attested_confidence, "
                    "quiz_category = :quiz_category, "
                    "quiz_difficulty = :quiz_difficulty, "
                    "is_quiz_eligible = :is_quiz_eligible"
                )

            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues=expression_values,
            )
            return True
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "update_approval_status",
                    "submission_id": submission_id,
                },
            )
            return False

    def _estimate_difficulty(self, item: Dict[str, Any]) -> QuizDifficulty:
        llm_result = item.get("llm_validation_result")
        if llm_result and llm_result.get("confidence"):
            confidence = float(llm_result["confidence"])
        else:
            confidence = float(item.get("llm_confidence_score", 0.85))

        if confidence >= 0.9:
            return QuizDifficulty.BEGINNER
        if confidence >= 0.7:
            return QuizDifficulty.INTERMEDIATE
        return QuizDifficulty.ADVANCED

    @tracer.trace_database_operation("update", "submissions")
    def add_upvote(self, submission_id: str, user_id: str, voter_user_id: str) -> bool:
        try:
            key = self._get_key_for_submission(submission_id)
            if not key:
                return False

            self.table.update_item(
                Key=key,
                UpdateExpression=(
                    "SET upvotes = if_not_exists(upvotes, :zero) + :inc "
                    "ADD upvoted_by :voter"
                ),
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":voter": {voter_user_id},
                },
            )
            return True
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "add_upvote",
                    "submission_id": submission_id,
                },
            )
            return False

    def upvote_submission(self, submission_id: str, voter_user_id: str) -> bool:
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return False
        return self.add_upvote(submission_id, submission.user_id, voter_user_id)

    @tracer.trace_database_operation("query", "validation_index")
    def get_by_validation_status(
        self, status: SlangSubmissionStatus, limit: int = 50
    ) -> List[SlangSubmission]:
        try:
            response = self.table.query(
                IndexName="ValidationStatusIndex",
                KeyConditionExpression="llm_validation_status = :status",
                ExpressionAttributeValues={":status": status.value},
                Limit=limit,
                ScanIndexForward=False,
            )
            return self._items_to_submissions(response.get("Items", []))
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "get_by_validation_status",
                    "status": status.value,
                },
            )
            return []

    @tracer.trace_database_operation("scan", "submissions")
    def check_duplicate_submission(
        self, slang_term: str, user_id: str, days: int = 7
    ) -> bool:
        """Check if user submitted the same term recently."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            response = self.table.query(
                IndexName="SubmissionsByUserIndex",
                KeyConditionExpression="user_id = :user_id",
                ExpressionAttributeValues={":user_id": user_id},
            )
            for item in response.get("Items", []):
                if (
                    item.get("slang_term") == slang_term
                    and item.get("created_at")
                    and datetime.fromisoformat(item["created_at"]) >= cutoff
                ):
                    return True
            return False
        except Exception as exc:
            logger.log_error(
                exc,
                {
                    "operation": "check_duplicate_submission",
                    "slang_term": slang_term,
                    "user_id": user_id,
                },
            )
            return False
