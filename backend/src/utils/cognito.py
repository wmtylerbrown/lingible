"""Simple Cognito utilities for user extraction."""

import os
from typing import Optional
from botocore.exceptions import ClientError

from .logging import logger
from .aws_services import aws_services
from .config import get_config
from ..models.aws import CognitoUserInfo
from aws_lambda_powertools.utilities.parser.models import (
    APIGatewayProxyEventModel as APIGatewayEvent,
)

# Get configuration
config = get_config()


class CognitoUserExtractor:
    """Extract user information from Cognito tokens."""

    def __init__(self) -> None:
        """Initialize Cognito user extractor."""
        self.user_pool_id = os.environ.get("USER_POOL_ID")

    @property
    def cognito_client(self):
        """Get Cognito client from centralized AWS services."""
        return aws_services.cognito_client

    def get_user_from_token(self, token: str) -> Optional[CognitoUserInfo]:
        """Get user info from Cognito token."""
        try:
            # Remove bearer prefix if present
            bearer_prefix = config.get_security_config()["bearer_prefix"]
            if token.startswith(bearer_prefix):
                token = token[len(bearer_prefix) :]

            # Get user info from Cognito
            response = self.cognito_client.get_user(AccessToken=token)

            # Use our typed model
            return CognitoUserInfo.from_cognito_response(response)

        except ClientError as e:
            logger.log_error(e, {"token_length": len(token) if token else 0})
            return None

    def extract_user_from_event(
        self, event: APIGatewayEvent
    ) -> Optional[CognitoUserInfo]:
        """Extract user from API Gateway event."""
        headers = event.headers or {}
        authorization = headers.get("Authorization") or headers.get("authorization")

        if not authorization:
            return None

        return self.get_user_from_token(authorization)


# Global instance
cognito_extractor = CognitoUserExtractor()
