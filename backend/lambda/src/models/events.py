"""Typed event models for Lambda handlers."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from aws_lambda_powertools.utilities.parser.models import (
    APIGatewayEventRequestContext,
    APIGatewayProxyEventModel,
)

from .translations import TranslationRequest
from .subscriptions import UserUpgradeRequest, AppleWebhookRequest
from .users import AccountDeletionRequest
from .slang import SlangSubmissionRequest


class TranslationEvent(BaseModel):
    """Typed event for translation handler."""

    # API Gateway event data
    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_body: TranslationRequest = Field(..., description="Parsed request body")

    # Extracted user info (guaranteed by envelope)
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )

    # Request metadata
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )
    timestamp: Optional[str] = Field(None, description="Request timestamp")


class UserProfileEvent(BaseModel):
    """Typed event for user profile handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class UserUsageEvent(BaseModel):
    """Typed event for user usage handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class SimpleAuthenticatedEvent(BaseModel):
    """Simple authenticated event for basic operations (GET, DELETE) that only need user info."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class SlangSubmissionEvent(BaseModel):
    """Typed event for slang submission handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_body: SlangSubmissionRequest = Field(..., description="Parsed request body")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class PathParameterEvent(BaseModel):
    """Authenticated event for operations that need path parameters (DELETE /{id}, etc.)."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )
    path_parameters: Dict[str, str] = Field(
        ..., description="Path parameters extracted by envelope"
    )


class HealthEvent(BaseModel):
    """Typed event for health check handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )
    timestamp: Optional[str] = Field(None, description="Request timestamp")


class TranslationHistoryEvent(BaseModel):
    """Typed event for translation history handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )

    # Query parameters
    limit: Optional[int] = Field(
        10, ge=1, le=100, description="Number of items to return"
    )
    offset: Optional[int] = Field(0, ge=0, description="Number of items to skip")


class SubscriptionEvent(BaseModel):
    """Typed event for subscription handlers."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class UserUpgradeEvent(BaseModel):
    """Typed event for user upgrade handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_body: UserUpgradeRequest = Field(..., description="Parsed request body")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class AccountDeletionEvent(BaseModel):
    """Typed event for account deletion handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_body: "AccountDeletionRequest" = Field(
        ..., description="Parsed request body"
    )
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )

    # Convenience properties for request body
    @property
    def confirmation_text(self) -> str:
        """Get confirmation text from request body."""
        return self.request_body.confirmation_text

    @property
    def reason(self) -> Optional[str]:
        """Get deletion reason from request body."""
        return self.request_body.reason


class AppleWebhookEvent(BaseModel):
    """Typed event for webhook handlers."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_body: AppleWebhookRequest = Field(..., description="Parsed request body")
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class CognitoUserAttributes(BaseModel):
    """Cognito user attributes."""

    sub: str = Field(..., description="User sub (user ID)")
    email: Optional[str] = Field(None, description="User email")
    email_verified: Optional[str] = Field(None, description="Email verification status")
    preferred_username: Optional[str] = Field(None, description="Preferred username")
    cognito_username: Optional[str] = Field(None, description="Cognito username")
    identities: Optional[str] = Field(None, description="Identity provider info")


class CognitoRequest(BaseModel):
    """Cognito request data."""

    userAttributes: CognitoUserAttributes = Field(..., description="User attributes")


class CognitoPostConfirmationEvent(BaseModel):
    """Typed event for Cognito post confirmation trigger."""

    version: str = Field(..., description="Event version")
    triggerSource: str = Field(..., description="Trigger source")
    region: str = Field(..., description="AWS region")
    userPoolId: str = Field(..., description="User pool ID")
    userName: str = Field(..., description="Username")
    request: CognitoRequest = Field(..., description="Request data")
    response: Dict[str, Any] = Field(..., description="Response data")


class CognitoPreAuthenticationEvent(BaseModel):
    """Typed event for Cognito pre authentication trigger."""

    version: str = Field(..., description="Event version")
    triggerSource: str = Field(..., description="Trigger source")
    region: str = Field(..., description="AWS region")
    userPoolId: str = Field(..., description="User pool ID")
    userName: str = Field(..., description="Username")
    request: CognitoRequest = Field(..., description="Request data")
    response: Dict[str, Any] = Field(..., description="Response data")


class CognitoPreTokenGenerationEvent(BaseModel):
    """Typed event for Cognito pre token generation trigger."""

    version: str = Field(..., description="Event version")
    triggerSource: str = Field(..., description="Trigger source")
    region: str = Field(..., description="AWS region")
    userPoolId: str = Field(..., description="User pool ID")
    userName: str = Field(..., description="Username")
    request: CognitoRequest = Field(..., description="Request data")
    response: Dict[str, Any] = Field(..., description="Response data")


class CognitoPreUserDeletionEvent(BaseModel):
    """Typed event for Cognito pre user deletion trigger."""

    version: str = Field(..., description="Event version")
    triggerSource: str = Field(..., description="Trigger source")
    region: str = Field(..., description="AWS region")
    userPoolId: str = Field(..., description="User pool ID")
    userName: str = Field(..., description="Username")
    request: CognitoRequest = Field(..., description="Request data")
    response: Dict[str, Any] = Field(..., description="Response data")


class UserDataCleanupEvent(BaseModel):
    """Typed event for user data cleanup handler."""

    user_id: str = Field(..., description="User ID to cleanup")
    deletion_reason: str = Field(..., description="Reason for deletion")
    cleanup_steps: List[str] = Field(
        default_factory=lambda: [
            "delete_translations",
            "delete_usage",
            "archive_subscriptions",
            "delete_other_data",
        ],
        description="List of cleanup steps to perform",
    )
    requested_at: Optional[str] = Field(None, description="When cleanup was requested")


class TrendingEvent(BaseModel):
    """Typed event for trending terms handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )

    # Query parameters
    limit: Optional[int] = Field(
        50, ge=1, le=100, description="Number of trending terms to return"
    )
    category: Optional[str] = Field(None, description="Filter by category")
    active_only: Optional[bool] = Field(
        True, description="Show only active trending terms"
    )


class PendingSubmissionsEvent(BaseModel):
    """Typed event for pending slang submissions handler."""

    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )

    # Query parameters
    limit: Optional[int] = Field(
        50, ge=1, le=100, description="Number of submissions to return"
    )


class SlangValidationEvent(BaseModel):
    """Event for async slang validation."""

    submission_id: str = Field(..., description="Slang submission ID to validate")
    user_id: str = Field(..., description="User ID who submitted the slang")
    slang_term: str = Field(..., description="The slang term to validate")
    context: Optional[str] = Field(None, description="Context for the slang term")


class CustomCognitoAuthorizerContext(BaseModel):
    # Standard JWT claims (always present)
    sub: str = Field(description="Subject - unique user identifier")
    aud: str = Field(description="Audience - client ID")
    iss: str = Field(description="Issuer - Cognito User Pool URL")
    exp: int = Field(description="Expiration time (Unix timestamp)")
    iat: int = Field(description="Issued at time (Unix timestamp)")
    jti: str = Field(description="JWT ID - unique token identifier")

    # User info (always present)
    email: str = Field(description="User email")

    # Cognito-specific claims (optional - Apple users won't have these)
    token_use: Optional[str] = Field(
        None, description="Token use type (id, access, refresh)"
    )
    auth_time: Optional[int] = Field(
        None, description="Authentication time (Unix timestamp)"
    )
    cognito_username: Optional[str] = Field(
        None, alias="cognito:username", description="Cognito username"
    )
    event_id: Optional[str] = Field(
        None, description="Event ID for this authentication"
    )
    origin_jti: Optional[str] = Field(None, description="Original JWT ID")

    # Apple-specific claims (optional - only for Apple users)
    at_hash: Optional[str] = Field(None, description="Apple OAuth access token hash")

    # Other optional claims
    email_verified: Optional[bool] = Field(
        None, description="Email verification status"
    )
    phone_number: Optional[str] = Field(None, description="User phone number")
    user_tier: Optional[str] = Field(
        None, alias="custom:user_tier", description="User tier (free, premium)"
    )
    role: Optional[str] = Field(None, alias="custom:role", description="User role")

    @field_validator("exp", "iat", "auth_time", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        """Parse timestamp from string or int."""
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                # Try to parse as Unix timestamp first
                return int(v)
            except ValueError:
                # If that fails, try to parse as datetime string
                try:
                    dt = datetime.strptime(v, "%a %b %d %H:%M:%S UTC %Y")
                    return int(dt.timestamp())
                except ValueError:
                    # If all else fails, return 0
                    return 0
        return 0


class CustomAPIGatewayEventAuthorizer(BaseModel):
    """Custom API Gateway event authorizer model for our Cognito authorizer."""

    claims: CustomCognitoAuthorizerContext = Field(description="Cognito claims")


class CustomRequestContext(APIGatewayEventRequestContext):
    """Custom request context that extends the base one with our custom authorizer."""

    authorizer: Optional[CustomAPIGatewayEventAuthorizer] = Field(None, description="Custom authorizer context")  # type: ignore[assignment]


class CustomAPIGatewayProxyEventModel(APIGatewayProxyEventModel):
    """API Gateway event with Lingible-specific validation."""

    # Override the request context to use our custom one
    requestContext: CustomRequestContext = Field(
        description="Request context with custom authorizer"
    )
