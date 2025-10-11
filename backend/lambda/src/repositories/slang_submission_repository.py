"""Repository for slang submission data operations."""

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
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service


class SlangSubmissionRepository:
    """Repository for slang submission data operations."""

    def __init__(self) -> None:
        """Initialize slang submission repository."""
        self.config_service = get_config_service()
        self.table_name = self.config_service._get_env_var("SLANG_SUBMISSIONS_TABLE")
        self.table = aws_services.get_table(self.table_name)

    def generate_submission_id(self) -> str:
        """Generate a unique submission ID."""
        return f"sub_{uuid.uuid4().hex[:16]}"

    @tracer.trace_database_operation("create", "slang_submission")
    def create_submission(self, submission: SlangSubmission) -> bool:
        """Create a new slang submission record."""
        try:
            item = {
                "PK": f"SUBMISSION#{submission.submission_id}",
                "SK": f"USER#{submission.user_id}",
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
                # GSI fields for querying by status
                "GSI1PK": f"STATUS#{submission.status}",
                "GSI1SK": submission.created_at.isoformat(),
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
    def get_submission(
        self, submission_id: str, user_id: str
    ) -> Optional[SlangSubmission]:
        """Get a submission by ID and user ID."""
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"SUBMISSION#{submission_id}",
                    "SK": f"USER#{user_id}",
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return self._item_to_submission(item)

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_submission",
                    "submission_id": submission_id,
                },
            )
            return None

    @tracer.trace_database_operation("query", "slang_submission")
    def get_submission_by_id(self, submission_id: str) -> Optional[SlangSubmission]:
        """
        Get a submission by ID only (scans for the submission).

        Used when we don't know the user_id (e.g., for upvoting).

        Args:
            submission_id: The submission ID

        Returns:
            SlangSubmission if found, None otherwise
        """
        try:
            # Query by PK only - since SK varies, we need to query the base table
            response = self.table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"SUBMISSION#{submission_id}"},
                Limit=1,
            )

            items = response.get("Items", [])
            if not items:
                return None

            return self._item_to_submission(items[0])

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_submission_by_id",
                    "submission_id": submission_id,
                },
            )
            return None

    @tracer.trace_database_operation("query", "slang_submission")
    def get_pending_submissions(self, limit: int = 50) -> List[SlangSubmission]:
        """Get pending submissions for review."""
        try:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :status",
                ExpressionAttributeValues={
                    ":status": f"STATUS#{ApprovalStatus.PENDING}"
                },
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )

            submissions = []
            for item in response.get("Items", []):
                try:
                    submissions.append(self._item_to_submission(item))
                except Exception as parse_error:
                    logger.log_error(
                        parse_error,
                        {
                            "operation": "parse_submission",
                            "submission_id": item.get("submission_id"),
                        },
                    )
                    continue

            return submissions

        except Exception as e:
            logger.log_error(e, {"operation": "get_pending_submissions"})
            return []

    @tracer.trace_database_operation("update", "slang_submission")
    def update_submission_status(
        self,
        submission_id: str,
        user_id: str,
        status: ApprovalStatus,
        reviewed_by: Optional[str] = None,
    ) -> bool:
        """Update the status of a submission."""
        try:
            reviewed_at = datetime.now(timezone.utc)

            update_expression = (
                "SET #status = :status, reviewed_at = :reviewed_at, GSI1PK = :gsi1pk"
            )
            expression_attribute_values = {
                ":status": str(status),
                ":reviewed_at": reviewed_at.isoformat(),
                ":gsi1pk": f"STATUS#{status}",
            }
            expression_attribute_names = {
                "#status": "status",
            }

            if reviewed_by:
                update_expression += ", reviewed_by = :reviewed_by"
                expression_attribute_values[":reviewed_by"] = reviewed_by

            self.table.update_item(
                Key={
                    "PK": f"SUBMISSION#{submission_id}",
                    "SK": f"USER#{user_id}",
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_submission_status",
                    "submission_id": submission_id,
                    "status": str(status),
                },
            )
            return False

    @tracer.trace_database_operation("query", "slang_submission")
    def get_user_submissions(
        self, user_id: str, limit: int = 20
    ) -> List[SlangSubmission]:
        """Get all submissions by a specific user."""
        try:
            response = self.table.query(
                IndexName="UserSubmissionsIndex",
                KeyConditionExpression="SK = :user_sk",
                ExpressionAttributeValues={":user_sk": f"USER#{user_id}"},
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )

            submissions = []
            for item in response.get("Items", []):
                try:
                    submissions.append(self._item_to_submission(item))
                except Exception as parse_error:
                    logger.log_error(
                        parse_error,
                        {
                            "operation": "parse_user_submission",
                            "submission_id": item.get("submission_id"),
                        },
                    )
                    continue

            return submissions

        except Exception as e:
            logger.log_error(
                e, {"operation": "get_user_submissions", "user_id": user_id}
            )
            return []

    @tracer.trace_database_operation("query", "slang_submission")
    def check_duplicate_submission(
        self, user_id: str, slang_term: str, days: int = 7
    ) -> bool:
        """Check if user has recently submitted the same term."""
        try:
            # Get recent submissions by user
            recent_submissions = self.get_user_submissions(user_id, limit=50)

            # Check for duplicate within time window
            cutoff_time = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)

            for submission in recent_submissions:
                if (
                    submission.slang_term.lower() == slang_term.lower()
                    and submission.created_at.timestamp() > cutoff_time
                ):
                    return True

            return False

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "check_duplicate_submission",
                    "user_id": user_id,
                    "slang_term": slang_term,
                },
            )
            # Return False on error to not block legitimate submissions
            return False

    @tracer.trace_database_operation("update", "slang_submission")
    def add_upvote(self, submission_id: str, user_id: str, voter_user_id: str) -> bool:
        """
        Add an upvote to a submission.

        Args:
            submission_id: The submission ID
            user_id: The submission owner's user ID
            voter_user_id: The user ID of the voter

        Returns:
            True if upvote was added successfully
        """
        try:
            self.table.update_item(
                Key={
                    "PK": f"SUBMISSION#{submission_id}",
                    "SK": f"USER#{user_id}",
                },
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

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "add_upvote",
                    "submission_id": submission_id,
                    "voter_user_id": voter_user_id,
                },
            )
            return False

    @tracer.trace_database_operation("query", "slang_submission")
    def get_by_validation_status(
        self, status: SlangSubmissionStatus, limit: int = 50
    ) -> List[SlangSubmission]:
        """
        Get submissions by validation status.

        Args:
            status: The validation status to query
            limit: Maximum number of submissions to return

        Returns:
            List of submissions with the specified status
        """
        try:
            response = self.table.query(
                IndexName="ValidationStatusIndex",
                KeyConditionExpression="llm_validation_status = :status",
                ExpressionAttributeValues={":status": str(status)},
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )

            submissions = []
            for item in response.get("Items", []):
                submissions.append(self._item_to_submission(item))

            return submissions

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "get_by_validation_status",
                    "status": str(status),
                },
            )
            return []

    @tracer.trace_database_operation("update", "slang_submission")
    def update_validation_result(
        self, submission_id: str, user_id: str, result: LLMValidationResult
    ) -> bool:
        """
        Update submission with LLM validation result.

        Args:
            submission_id: The submission ID
            user_id: The submission owner's user ID
            result: The LLM validation result

        Returns:
            True if update was successful
        """
        try:
            # Serialize validation result
            validation_result_dict = result.model_dump()
            # Convert Decimal to string for JSON storage
            validation_result_dict["confidence"] = str(result.confidence)
            validation_result_dict["validated_at"] = result.validated_at.isoformat()

            # Convert evidence list
            validation_result_dict["evidence"] = [
                ev.model_dump() for ev in result.evidence
            ]

            self.table.update_item(
                Key={
                    "PK": f"SUBMISSION#{submission_id}",
                    "SK": f"USER#{user_id}",
                },
                UpdateExpression=(
                    "SET llm_confidence_score = :confidence, "
                    "llm_validation_result = :result"
                ),
                ExpressionAttributeValues={
                    ":confidence": str(result.confidence),
                    ":result": validation_result_dict,
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
        validation_status: SlangSubmissionStatus,
        approval_type: ApprovalType,
        approved_by: Optional[str] = None,
    ) -> bool:
        """
        Update submission approval status.

        Args:
            submission_id: The submission ID
            user_id: The submission owner's user ID
            validation_status: The new validation status
            approval_type: The type of approval
            approved_by: User ID of admin who approved (if manual)

        Returns:
            True if update was successful
        """
        try:
            update_expression = (
                "SET llm_validation_status = :status, "
                "approval_type = :approval_type, "
                "reviewed_at = :reviewed_at"
            )
            expression_values = {
                ":status": str(validation_status),
                ":approval_type": str(approval_type),
                ":reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

            if approved_by:
                update_expression += ", approved_by = :approved_by"
                expression_values[":approved_by"] = approved_by

            # Update approval status in main status field if approved
            if validation_status in [
                SlangSubmissionStatus.AUTO_APPROVED,
                SlangSubmissionStatus.ADMIN_APPROVED,
            ]:
                update_expression += ", #status = :approved_status, GSI1PK = :gsi1pk"
                expression_values[":approved_status"] = str(ApprovalStatus.APPROVED)
                expression_values[":gsi1pk"] = f"STATUS#{ApprovalStatus.APPROVED}"

            self.table.update_item(
                Key={
                    "PK": f"SUBMISSION#{submission_id}",
                    "SK": f"USER#{user_id}",
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=(
                    {"#status": "status"} if "status" in update_expression else {}
                ),
            )
            return True

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "update_approval_status",
                    "submission_id": submission_id,
                    "status": str(validation_status),
                },
            )
            return False

    def _item_to_submission(self, item: dict) -> SlangSubmission:
        """
        Convert DynamoDB item to SlangSubmission model.

        Args:
            item: DynamoDB item dict

        Returns:
            SlangSubmission model
        """
        # Parse validation result if present
        llm_validation_result = None
        if item.get("llm_validation_result"):
            try:
                result_data = item["llm_validation_result"]
                llm_validation_result = LLMValidationResult(
                    is_valid=result_data.get("is_valid", False),
                    confidence=Decimal(str(result_data.get("confidence", "0.5"))),
                    evidence=[
                        LLMValidationEvidence(
                            source=ev.get("source", "unknown"),
                            example=ev.get("example", ""),
                        )
                        for ev in result_data.get("evidence", [])
                    ],
                    recommended_definition=result_data.get("recommended_definition"),
                    usage_score=result_data.get("usage_score", 5),
                    validated_at=datetime.fromisoformat(result_data["validated_at"]),
                )
            except Exception as e:
                logger.log_error(
                    e,
                    {
                        "operation": "parse_validation_result",
                        "submission_id": item.get("submission_id"),
                    },
                )

        return SlangSubmission(
            submission_id=item["submission_id"],
            user_id=item["user_id"],
            slang_term=item["slang_term"],
            meaning=item["meaning"],
            example_usage=item.get("example_usage"),
            context=item["context"],
            original_translation_id=item.get("original_translation_id"),
            status=ApprovalStatus(item["status"]),
            created_at=datetime.fromisoformat(item["created_at"]),
            reviewed_at=(
                datetime.fromisoformat(item["reviewed_at"])
                if item.get("reviewed_at")
                else None
            ),
            reviewed_by=item.get("reviewed_by"),
            llm_validation_status=SlangSubmissionStatus(
                item.get("llm_validation_status", "pending_validation")
            ),
            llm_confidence_score=(
                Decimal(str(item["llm_confidence_score"]))
                if item.get("llm_confidence_score")
                else None
            ),
            llm_validation_result=llm_validation_result,
            approval_type=(
                ApprovalType(item["approval_type"])
                if item.get("approval_type")
                else None
            ),
            approved_by=item.get("approved_by"),
            upvotes=item.get("upvotes", 0),
            upvoted_by=list(item.get("upvoted_by", set())),
        )
