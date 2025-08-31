"""Cognito post confirmation trigger handler for user creation."""

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.parser.models import CognitoPostConfirmationTriggerModel

from services.user_service import UserService
from utils.tracing import tracer
from utils.logging import logger
from models.users import UserTier


# Initialize service at module level for Lambda container reuse
user_service = UserService()


@tracer.trace_lambda
@event_parser(model=CognitoPostConfirmationTriggerModel)
def handler(
    event: CognitoPostConfirmationTriggerModel, context: LambdaContext
) -> dict:
    """Create user record in DynamoDB after Cognito user confirmation."""
    try:
        # Use the actual Cognito UUID as user_id, not the login username
        user_id = event.request.userAttributes["sub"]
        email = event.request.userAttributes["email"]
        username = event.request.userAttributes.get("preferred_username") or event.userName

        logger.log_business_event(
            "cognito_user_confirmed",
            {
                "user_id": user_id,
                "email": email,
                "username": username,
            },
        )

        # Create user record in our system
        user = user_service.create_user(
            user_id=user_id,
            username=username,
            email=email,
            tier=UserTier.FREE
        )

        # If we get here, user was created successfully
        logger.log_business_event(
            "user_created_in_system",
            {
                "user_id": user_id,
                "username": user.username,
                "tier": user.tier,
            },
        )

        return event.model_dump()

    except Exception as e:
        logger.log_error(
            e,
            {
                "operation": "post_confirmation_handler",
                "user_id": getattr(event, 'userName', 'unknown'),
            },
        )
        # Don't fail the confirmation - return event to allow Cognito confirmation to proceed
        return event.model_dump()
