"""Service for managing user-submitted slang terms."""

import json
from datetime import datetime, timezone
from typing import List

from models.slang import (
    LLMValidationResult,
    SlangSubmission,
    SlangSubmissionRequest,
    SlangSubmissionResponse,
    ApprovalStatus,
    SlangSubmissionStatus,
    ApprovalType,
    UpvoteResponse,
    PendingSubmissionsResponse,
    AdminApprovalResponse,
)
from models.config import SlangSubmissionConfig
from models.users import UserTier
from repositories.slang_term_repository import SlangTermRepository
from services.user_service import UserService
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service
from utils.exceptions import (
    ValidationError,
    InsufficientPermissionsError,
    BusinessLogicError,
    ResourceNotFoundError,
)


class SlangSubmissionService:
    """Service for handling slang submissions from users."""

    # Rate limiting configuration
    MAX_SUBMISSIONS_PER_DAY = 10
    DUPLICATE_CHECK_DAYS = 7

    def __init__(self) -> None:
        """Initialize slang submission service."""
        self.repository = SlangTermRepository()
        self.user_service = UserService()
        self.config_service = get_config_service()
        self.submission_config = self.config_service.get_config(SlangSubmissionConfig)
        self.sns_client = aws_services.sns_client

    @tracer.trace_method("submit_slang")
    def submit_slang(
        self, request: SlangSubmissionRequest, user_id: str
    ) -> SlangSubmissionResponse:
        """
        Submit a new slang term for review.

        Premium feature only.
        Includes validation, duplicate checking, and rate limiting.
        """
        # Validate user has premium access
        if not self._is_premium_user(user_id):
            raise InsufficientPermissionsError(
                message="Slang submissions are a premium feature. Upgrade to submit new slang terms!"
            )

        # Validate and sanitize input
        self._validate_submission(request)

        # Check for duplicates
        if self.repository.check_duplicate_submission(
            request.slang_term, user_id, self.DUPLICATE_CHECK_DAYS
        ):
            raise ValidationError(
                f"You've already submitted '{request.slang_term}' recently. Check back later to see if it was approved!"
            )

        # Check rate limit
        if not self._check_rate_limit(user_id):
            raise BusinessLogicError(
                f"You've reached your daily limit of {self.MAX_SUBMISSIONS_PER_DAY} submissions. Try again tomorrow!"
            )

        # Create submission
        submission_id = self.repository.generate_submission_id()
        submission = SlangSubmission(
            submission_id=submission_id,
            user_id=user_id,
            slang_term=request.slang_term.strip(),
            meaning=request.meaning.strip(),
            example_usage=(
                request.example_usage.strip() if request.example_usage else None
            ),
            context=request.context,
            original_translation_id=request.translation_id,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            reviewed_at=None,
            reviewed_by=None,
            llm_validation_status=SlangSubmissionStatus.PENDING_VALIDATION,
            llm_confidence_score=None,
            llm_validation_result=None,
            approval_type=None,
            approved_by=None,
            upvotes=0,
            upvoted_by=[],
        )

        # Save to database
        success = self.repository.create_submission(submission)

        if not success:
            raise BusinessLogicError(
                "Failed to save your submission. Please try again."
            )

        # Increment user's submitted count
        self.user_service.increment_slang_submitted(user_id)

        # Log business event
        logger.log_business_event(
            "slang_submission_created",
            {
                "submission_id": submission_id,
                "user_id": user_id,
                "slang_term": request.slang_term,
                "context": str(request.context),
            },
        )

        # Publish to validation topic for async validation
        self._publish_validation_request(submission)

        return SlangSubmissionResponse(
            submission_id=submission_id,
            status=ApprovalStatus.PENDING,
            message="Thanks for the submission! We're checking it out now. No cap, we appreciate your help!",
            created_at=submission.created_at,
        )

    def get_user_submissions(
        self, user_id: str, limit: int = 20
    ) -> List[SlangSubmission]:
        """Get all submissions by a user (premium feature)."""
        if not self._is_premium_user(user_id):
            raise InsufficientPermissionsError(
                message="Viewing your submissions is a premium feature."
            )

        return self.repository.get_user_submissions(user_id, limit)

    def approve_submission(
        self, submission_id: str, user_id: str, reviewer_id: str
    ) -> bool:
        """Approve a submission (admin only)."""
        # Get the submission to verify it exists and get the submission owner
        submission = self.repository.get_submission_by_id(submission_id)
        if not submission:
            return False

        # Update approval status
        success = self.repository.update_approval_status(
            submission_id,
            submission.user_id,
            SlangSubmissionStatus.ADMIN_APPROVED,
            ApprovalType.ADMIN_MANUAL,
        )

        if not success:
            return False

        # Update main status to approved
        # Note: This method doesn't exist yet in repository - may need to be added
        # For now, the approval status update above should be sufficient
        return True

    def reject_submission(
        self, submission_id: str, user_id: str, reviewer_id: str
    ) -> bool:
        """Reject a submission (admin only)."""
        # Get the submission to verify it exists and get the submission owner
        submission = self.repository.get_submission_by_id(submission_id)
        if not submission:
            return False

        # Update approval status
        success = self.repository.update_approval_status(
            submission_id,
            submission.user_id,
            SlangSubmissionStatus.REJECTED,
            ApprovalType.ADMIN_MANUAL,
        )

        if not success:
            return False

        # Update main status to rejected
        # Note: This method doesn't exist yet in repository - may need to be added
        # For now, the approval status update above should be sufficient
        return True

    def _is_premium_user(self, user_id: str) -> bool:
        """Check if user has premium access."""
        try:
            user = self.user_service.get_user(user_id)
            if user and user.tier == UserTier.PREMIUM:
                return True
            return False
        except Exception as e:
            logger.log_error(
                e, {"operation": "check_premium_status", "user_id": user_id}
            )
            return False

    def _validate_submission(self, request: SlangSubmissionRequest) -> None:
        """Validate submission request."""
        # Sanitize and validate slang_term
        if not request.slang_term or not request.slang_term.strip():
            raise ValidationError("Slang term cannot be empty")

        if len(request.slang_term.strip()) > 100:
            raise ValidationError("Slang term is too long (max 100 characters)")

        # Sanitize and validate meaning
        if not request.meaning or not request.meaning.strip():
            raise ValidationError("Meaning cannot be empty")

        if len(request.meaning.strip()) > 500:
            raise ValidationError("Meaning is too long (max 500 characters)")

        # Validate example_usage if provided
        if request.example_usage and len(request.example_usage.strip()) > 500:
            raise ValidationError("Example usage is too long (max 500 characters)")

        # Check for potentially inappropriate content (basic filter)
        prohibited_words = ["test", "spam"]  # Placeholder - would use a real filter
        slang_lower = request.slang_term.lower()

        # This is a very basic check - in production you'd use a proper content filter
        if any(word in slang_lower for word in prohibited_words):
            logger.log_business_event(
                "submission_blocked",
                {
                    "slang_term": request.slang_term,
                    "reason": "prohibited_content",
                },
            )
            raise ValidationError("This submission contains prohibited content")

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within daily submission limit."""
        try:
            # Get user's submissions from today
            user_submissions = self.repository.get_user_submissions(user_id, limit=100)

            # Count submissions from last 24 hours
            now = datetime.now(timezone.utc)
            today_start = now.timestamp() - (24 * 60 * 60)

            recent_count = sum(
                1
                for sub in user_submissions
                if sub.created_at.timestamp() > today_start
            )

            if recent_count >= self.MAX_SUBMISSIONS_PER_DAY:
                logger.log_business_event(
                    "submission_rate_limited",
                    {
                        "user_id": user_id,
                        "submission_count": recent_count,
                        "limit": self.MAX_SUBMISSIONS_PER_DAY,
                    },
                )
                return False

            return True

        except Exception as e:
            logger.log_error(e, {"operation": "check_rate_limit", "user_id": user_id})
            # On error, allow submission (fail open)
            return True

    def _publish_submission_notification(self, submission: SlangSubmission) -> None:
        """Publish SNS notification for new submission."""
        try:
            topic_arn = self.submission_config.submissions_topic_arn

            message = {
                "submission_id": submission.submission_id,
                "user_id": submission.user_id,
                "slang_term": submission.slang_term,
                "meaning": submission.meaning,
                "example_usage": submission.example_usage,
                "context": str(submission.context),
                "created_at": submission.created_at.isoformat(),
                "notification_type": "new_submission",
            }

            self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=f"New Slang Submission: {submission.slang_term}",
                Message=json.dumps(message, indent=2),
            )

            logger.log_business_event(
                "submission_notification_sent",
                {"submission_id": submission.submission_id},
            )

        except Exception as e:
            # Log but don't fail the submission if notification fails
            logger.log_error(
                e,
                {
                    "operation": "publish_submission_notification",
                    "submission_id": submission.submission_id,
                },
            )

    def _publish_auto_approval_notification(
        self, submission: SlangSubmission, validation_result: LLMValidationResult
    ) -> None:
        """Publish SNS notification for auto-approved submission."""
        try:
            topic_arn = self.submission_config.submissions_topic_arn

            message = {
                "submission_id": submission.submission_id,
                "user_id": submission.user_id,
                "slang_term": submission.slang_term,
                "meaning": submission.meaning,
                "example_usage": submission.example_usage,
                "created_at": submission.created_at.isoformat(),
                "notification_type": "auto_approval",
                "confidence_score": float(validation_result.confidence),
                "usage_score": validation_result.usage_score,
                "approved_at": (
                    submission.reviewed_at.isoformat()
                    if submission.reviewed_at
                    else submission.created_at.isoformat()
                ),
            }

            self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=f"✅ Auto-Approved: {submission.slang_term}",
                Message=json.dumps(message, indent=2),
                MessageAttributes={
                    "notification_type": {
                        "DataType": "String",
                        "StringValue": "auto_approval",
                    }
                },
            )

            logger.log_business_event(
                "auto_approval_notification_sent",
                {"submission_id": submission.submission_id},
            )

        except Exception as e:
            # Log but don't fail the submission if notification fails
            logger.log_error(
                e,
                {
                    "operation": "publish_auto_approval_notification",
                    "submission_id": submission.submission_id,
                },
            )

    def _publish_approval_notification(self, submission: SlangSubmission) -> None:
        """Publish SNS notification for manually approved submission."""
        try:
            topic_arn = self.submission_config.submissions_topic_arn

            from datetime import datetime, timezone

            message = {
                "submission_id": submission.submission_id,
                "user_id": submission.user_id,
                "slang_term": submission.slang_term,
                "meaning": submission.meaning,
                "example_usage": submission.example_usage,
                "created_at": submission.created_at.isoformat(),
                "notification_type": "manual_approval",
                "approved_at": (
                    submission.reviewed_at.isoformat()
                    if submission.reviewed_at
                    else datetime.now(timezone.utc).isoformat()
                ),
            }

            self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=f"✅ Manually Approved: {submission.slang_term}",
                Message=json.dumps(message, indent=2),
                MessageAttributes={
                    "notification_type": {
                        "DataType": "String",
                        "StringValue": "manual_approval",
                    }
                },
            )

            logger.log_business_event(
                "manual_approval_notification_sent",
                {"submission_id": submission.submission_id},
            )

        except Exception as e:
            # Log but don't fail the submission if notification fails
            logger.log_error(
                e,
                {
                    "operation": "publish_approval_notification",
                    "submission_id": submission.submission_id,
                },
            )

    def _publish_validation_request(self, submission: SlangSubmission) -> None:
        """Publish validation request to SNS."""
        try:
            topic_arn = self.submission_config.validation_request_topic_arn
            if not topic_arn:
                logger.log_error(
                    Exception(
                        "SLANG_VALIDATION_REQUEST_TOPIC_ARN environment variable not set"
                    ),
                    {"operation": "publish_validation_request"},
                )
                return

            message = {
                "submission_id": submission.submission_id,
                "user_id": submission.user_id,
                "slang_term": submission.slang_term,
                "context": submission.context,
            }

            self.sns_client.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject="Slang Validation Request",
            )

            logger.log_business_event(
                "validation_request_published",
                {
                    "submission_id": submission.submission_id,
                    "slang_term": submission.slang_term,
                },
            )

        except Exception as e:
            # Log but don't fail the submission if validation request fails
            logger.log_error(
                e,
                {
                    "operation": "publish_validation_request",
                    "submission_id": submission.submission_id,
                },
            )

    @tracer.trace_method("upvote_submission")
    def upvote_submission(
        self, submission_id: str, voter_user_id: str
    ) -> UpvoteResponse:
        """
        Add an upvote to a submission.

        Args:
            submission_id: The submission ID
            voter_user_id: The user ID of the voter

        Returns:
            UpvoteResponse with updated upvote count

        Raises:
            ValidationError: If user tries to upvote their own submission
            ResourceNotFoundError: If submission not found
        """
        # Get the submission (by ID only since voter doesn't know owner)
        submission = self.repository.get_submission_by_id(submission_id)
        if not submission:
            raise ResourceNotFoundError("submission", submission_id)

        # Check if user is trying to upvote their own submission
        if submission.user_id == voter_user_id:
            raise ValidationError("You can't upvote your own submission!")

        # Check if user has already upvoted
        if voter_user_id in submission.upvoted_by:
            raise ValidationError("You've already upvoted this submission!")

        # Add the upvote
        success = self.repository.upvote_submission(submission_id, voter_user_id)
        if not success:
            raise BusinessLogicError("Failed to add upvote. Please try again.")

        # Get updated submission
        updated_submission = self.repository.get_submission_by_id(submission_id)
        upvotes = (
            updated_submission.upvotes if updated_submission else submission.upvotes + 1
        )

        logger.log_business_event(
            "submission_upvoted",
            {
                "submission_id": submission_id,
                "voter_user_id": voter_user_id,
                "total_upvotes": upvotes,
            },
        )

        return UpvoteResponse(
            submission_id=submission_id,
            upvotes=upvotes,
            message="Thanks for the upvote!",
        )

    @tracer.trace_method("get_pending_submissions")
    def get_pending_submissions(self, limit: int = 50) -> PendingSubmissionsResponse:
        """
        Get submissions available for community voting.

        Returns submissions that are VALIDATED (ready for upvoting).

        Args:
            limit: Maximum number of submissions to return

        Returns:
            PendingSubmissionsResponse with list of submissions
        """
        submissions = self.repository.get_validated_submissions_for_voting(limit=limit)

        return PendingSubmissionsResponse(
            submissions=submissions,
            total_count=len(submissions),
            has_more=len(submissions) >= limit,
        )

    @tracer.trace_method("admin_approve")
    def admin_approve(
        self, submission_id: str, admin_user_id: str
    ) -> AdminApprovalResponse:
        """
        Manually approve a submission (admin only).

        Args:
            submission_id: The submission ID
            admin_user_id: The admin user ID

        Returns:
            AdminApprovalResponse with updated status

        Raises:
            ResourceNotFoundError: If submission not found
        """
        # Get the submission to verify it exists
        submission = self.repository.get_submission_by_id(submission_id)
        if not submission:
            raise ResourceNotFoundError("submission", submission_id)

        # Update to approved status
        success = self.repository.update_approval_status(
            submission_id,
            submission.user_id,
            SlangSubmissionStatus.ADMIN_APPROVED,
            ApprovalType.ADMIN_MANUAL,
        )

        if not success:
            raise BusinessLogicError("Failed to approve submission")

        # Note: update_submission_status doesn't exist in repository
        # The approval status update above handles the status change

        # Increment user's approved count
        self.user_service.increment_slang_approved(submission.user_id)

        logger.log_business_event(
            "slang_admin_approved",
            {
                "submission_id": submission_id,
                "slang_term": submission.slang_term,
                "admin_user_id": admin_user_id,
            },
        )

        # Publish approval notification to trigger lexicon export
        self._publish_approval_notification(submission)

        return AdminApprovalResponse(
            submission_id=submission_id,
            status=ApprovalStatus.APPROVED,
            message=f"Approved '{submission.slang_term}' and added to database",
        )

    @tracer.trace_method("admin_reject")
    def admin_reject(
        self, submission_id: str, admin_user_id: str
    ) -> AdminApprovalResponse:
        """
        Manually reject a submission (admin only).

        Args:
            submission_id: The submission ID
            admin_user_id: The admin user ID

        Returns:
            AdminApprovalResponse with updated status

        Raises:
            ResourceNotFoundError: If submission not found
        """
        # Get the submission to verify it exists
        submission = self.repository.get_submission_by_id(submission_id)
        if not submission:
            raise ResourceNotFoundError("submission", submission_id)

        # Update to rejected status
        success = self.repository.update_approval_status(
            submission_id,
            submission.user_id,
            SlangSubmissionStatus.REJECTED,
            ApprovalType.ADMIN_MANUAL,
        )

        if not success:
            raise BusinessLogicError("Failed to reject submission")

        # Note: update_submission_status doesn't exist in repository
        # The approval status update above handles the status change

        logger.log_business_event(
            "slang_admin_rejected",
            {
                "submission_id": submission_id,
                "slang_term": submission.slang_term,
                "admin_user_id": admin_user_id,
            },
        )

        return AdminApprovalResponse(
            submission_id=submission_id,
            status=ApprovalStatus.REJECTED,
            message=f"Rejected '{submission.slang_term}'",
        )
