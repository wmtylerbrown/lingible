"""Typed event models for Lambda handlers."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from .translations import TranslationRequest
from .subscriptions import UserUpgradeRequest, AppleWebhookRequest


class TranslationEvent(BaseModel):
    """Typed event for translation handler."""

    # API Gateway event data
    event: Dict[str, Any] = Field(..., description="Raw API Gateway event")
    request_body: TranslationRequest = Field(..., description="Parsed request body")

    # Extracted user info (guaranteed by envelope)
    user_id: str = Field(
        ..., description="User ID from Cognito token (guaranteed by envelope)"
    )
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
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
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
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
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
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
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
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
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
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
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
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
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
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
    username: str = Field(
        ..., description="Username from Cognito token (guaranteed by envelope)"
    )
    request_id: str = Field(
        ..., description="Request ID for tracing (guaranteed by envelope)"
    )


class WebhookEvent(BaseModel):
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
