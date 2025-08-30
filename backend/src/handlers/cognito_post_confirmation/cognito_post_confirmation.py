"""Cognito post confirmation trigger handler for user creation."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from ...models.events import CognitoPostConfirmationEvent
from ...services.user_service import UserService
from ...utils.tracing import tracer
from ...utils.logging import logger
from datetime import datetime, timezone
from ...models.users import User, UserTier, UserStatus


# Initialize service at module level for Lambda container reuse
user_service = UserService()


@event_parser(model=CognitoPostConfirmationEvent)
@tracer.trace_method("cognito_post_confirmation")
def post_confirmation_handler(
    event: CognitoPostConfirmationEvent, context: LambdaContext
) -> CognitoPostConfirmationEvent:
    """Create user record in DynamoDB after Cognito user confirmation."""
    try:
        user_id = event.userName
        user_attributes = event.request.userAttributes

        logger.log_business_event(
            "cognito_user_confirmed",
            {
                "user_id": user_id,
                "email": user_attributes.email,
                "username": user_attributes.preferred_username,
            },
        )

        # Create user record in our system
        user = User(
            user_id=user_id,
            username=user_attributes.preferred_username or user_id,
            email=user_attributes.email or "",  # Handle None case
            tier=UserTier.FREE,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        success = user_service.create_user(user)
        if success:
            logger.log_business_event(
                "user_created_in_system",
                {
                    "user_id": user_id,
                    "username": user.username,
                    "tier": user.tier.value,
                },
            )
        else:
            logger.log_error(
                Exception("Failed to create user in system"),
                {"user_id": user_id, "operation": "post_confirmation"},
            )

        return event

    except Exception as e:
        logger.log_error(
            e,
            {
                "operation": "post_confirmation_handler",
                "user_id": event.userName if hasattr(event, "userName") else "unknown",
            },
        )
        # Don't fail the confirmation - return event to allow Cognito confirmation to proceed
        return event
