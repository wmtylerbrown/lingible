"""Cognito post confirmation trigger handler for automatic user creation."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from ..models.events import CognitoPostConfirmationEvent
from ..services.user_service import UserService
from ..utils.tracing import tracer
from ..utils.logging import logger


# Initialize service at module level for Lambda container reuse
user_service = UserService()


@event_parser(model=CognitoPostConfirmationEvent)
@tracer.trace_method("cognito_post_confirmation")
def post_confirmation_handler(
    event: CognitoPostConfirmationEvent, context: LambdaContext
) -> CognitoPostConfirmationEvent:
    """Create user in DynamoDB after Cognito email confirmation."""
    try:
        user_id = event.userName
        user_attributes = event.request.userAttributes

        logger.log_business_event(
            "cognito_user_confirmed",
            {
                "user_id": user_id,
                "email": user_attributes.email,
                "signup_source": user_attributes.identities or "direct",
            },
        )

        # Check if user already exists in our system
        existing_user = user_service.get_user(user_id)
        if existing_user:
            logger.log_business_event(
                "user_already_exists",
                {"user_id": user_id, "operation": "post_confirmation"},
            )
            return event

        # Create user in our system
        username = (
            user_attributes.preferred_username
            or user_attributes.cognito_username
            or user_id
        )
        email = user_attributes.email or ""

        user = user_service.create_user(user_id=user_id, username=username, email=email)

        logger.log_business_event(
            "user_created_from_cognito",
            {
                "user_id": user_id,
                "username": username,
                "email": email,
                "tier": user.tier.value,
            },
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
        # Don't fail the Cognito flow - return event to allow signup to complete
        return event
