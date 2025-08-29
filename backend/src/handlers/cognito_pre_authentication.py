"""Cognito pre authentication trigger handler for ensuring user exists in DynamoDB."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from ..models.events import CognitoPreAuthenticationEvent
from ..services.user_service import UserService
from ..utils.tracing import tracer
from ..utils.logging import logger


# Initialize service at module level for Lambda container reuse
user_service = UserService()


@event_parser(model=CognitoPreAuthenticationEvent)
@tracer.trace_method("cognito_pre_authentication")
def pre_authentication_handler(
    event: CognitoPreAuthenticationEvent, context: LambdaContext
) -> CognitoPreAuthenticationEvent:
    """Ensure user exists in DynamoDB before authentication (handles Sign in with Apple)."""
    try:
        user_id = event.userName
        user_attributes = event.request.userAttributes

        logger.log_business_event(
            "cognito_pre_authentication",
            {
                "user_id": user_id,
                "email": user_attributes.email,
                "signup_source": user_attributes.identities or "direct",
            },
        )

        # Check if user exists in our system
        existing_user = user_service.get_user(user_id)
        if existing_user:
            logger.log_business_event(
                "user_exists_during_auth",
                {"user_id": user_id, "tier": existing_user.tier.value},
            )
            return event

        # Create user if missing (handles Sign in with Apple users who bypassed post_confirmation)
        username = (
            user_attributes.preferred_username
            or user_attributes.cognito_username
            or user_id
        )
        email = user_attributes.email or ""

        user = user_service.create_user(user_id=user_id, username=username, email=email)

        logger.log_business_event(
            "user_created_during_auth",
            {
                "user_id": user_id,
                "username": username,
                "email": email,
                "tier": user.tier.value,
                "source": "pre_authentication",
            },
        )

        return event

    except Exception as e:
        logger.log_error(
            e,
            {
                "operation": "pre_authentication_handler",
                "user_id": event.userName if hasattr(event, "userName") else "unknown",
            },
        )
        # Don't fail the authentication - return event to allow login to proceed
        return event
