"""Cognito pre authentication trigger handler for login validation."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from ...models.events import CognitoPreAuthenticationEvent
from ...services.user_service import UserService
from ...utils.tracing import tracer
from ...utils.logging import logger


# Initialize service at module level for Lambda container reuse
user_service = UserService()


@event_parser(model=CognitoPreAuthenticationEvent)
@tracer.trace_method("cognito_pre_authentication")
def pre_authentication_handler(
    event: CognitoPreAuthenticationEvent, context: LambdaContext
) -> CognitoPreAuthenticationEvent:
    """Validate user before authentication."""
    try:
        user_id = event.userName
        user_attributes = event.request.userAttributes

        logger.log_business_event(
            "cognito_pre_authentication",
            {
                "user_id": user_id,
                "email": user_attributes.email,
            },
        )

        # Check if user exists in our system
        existing_user = user_service.get_user(user_id)
        if not existing_user:
            logger.log_business_event(
                "user_not_found_for_authentication",
                {"user_id": user_id},
            )
            # Don't block authentication - user might be created later
            return event

        # Check if user is active
        if existing_user.status.value != "ACTIVE":
            logger.log_business_event(
                "user_authentication_blocked",
                {
                    "user_id": user_id,
                    "status": existing_user.status.value,
                },
            )
            # Block authentication for inactive users
            raise Exception(f"User account is {existing_user.status.value}")

        logger.log_business_event(
            "user_authentication_allowed",
            {
                "user_id": user_id,
                "tier": existing_user.tier.value,
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
        # Re-raise to block authentication
        raise
