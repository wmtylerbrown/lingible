"""Service for managing user-submitted slang terms."""

import json
from datetime import datetime, timezone
from typing import List

from models.slang import (
    SlangSubmission,
    SlangSubmissionRequest,
    SlangSubmissionResponse,
    ApprovalStatus,
)
from models.users import UserTier
from repositories.slang_submission_repository import SlangSubmissionRepository
from services.user_service import UserService
from utils.smart_logger import logger
from utils.tracing import tracer
from utils.aws_services import aws_services
from utils.config import get_config_service
from utils.exceptions import (
    ValidationError,
    InsufficientPermissionsError,
    BusinessLogicError,
)


class SlangSubmissionService:
    """Service for handling slang submissions from users."""

    # Rate limiting configuration
    MAX_SUBMISSIONS_PER_DAY = 10
    DUPLICATE_CHECK_DAYS = 7

    def __init__(self) -> None:
        """Initialize slang submission service."""
        self.repository = SlangSubmissionRepository()
        self.user_service = UserService()
        self.config_service = get_config_service()
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
            user_id, request.slang_term, self.DUPLICATE_CHECK_DAYS
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
        )

        # Save to database
        success = self.repository.create_submission(submission)

        if not success:
            raise BusinessLogicError(
                "Failed to save your submission. Please try again."
            )

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

        # Notify admins via SNS
        self._publish_submission_notification(submission)

        return SlangSubmissionResponse(
            submission_id=submission_id,
            status=ApprovalStatus.PENDING,
            message="Thanks for the submission! We'll review it soon. No cap, we appreciate your help!",
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

    def get_pending_submissions(self, limit: int = 50) -> List[SlangSubmission]:
        """Get pending submissions for admin review."""
        return self.repository.get_pending_submissions(limit)

    def approve_submission(
        self, submission_id: str, user_id: str, reviewer_id: str
    ) -> bool:
        """Approve a submission (admin only)."""
        return self.repository.update_submission_status(
            submission_id, user_id, ApprovalStatus.APPROVED, reviewer_id
        )

    def reject_submission(
        self, submission_id: str, user_id: str, reviewer_id: str
    ) -> bool:
        """Reject a submission (admin only)."""
        return self.repository.update_submission_status(
            submission_id, user_id, ApprovalStatus.REJECTED, reviewer_id
        )

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
            topic_arn = self.config_service._get_env_var("SLANG_SUBMISSIONS_TOPIC_ARN")

            message = {
                "submission_id": submission.submission_id,
                "user_id": submission.user_id,
                "slang_term": submission.slang_term,
                "meaning": submission.meaning,
                "example_usage": submission.example_usage,
                "context": str(submission.context),
                "created_at": submission.created_at.isoformat(),
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
