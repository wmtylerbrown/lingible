"""
Pydantic models for Lambda configuration.

These models provide type safety and validation for configuration
loaded from environment variables and secrets.
"""

from typing import List
from pydantic import BaseModel, Field
from enum import Enum


class LogLevel(str, Enum):
    """Logging level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BedrockConfig(BaseModel):
    """Bedrock configuration - only fields used in Python code."""
    model: str = Field(description="Required: Bedrock model ID")
    max_tokens: int = Field(description="Maximum tokens for Bedrock requests")
    temperature: float = Field(description="Temperature for Bedrock requests")


class UsageLimitsConfig(BaseModel):
    """Usage limits configuration."""
    free_daily_translations: int = Field(description="Free tier daily translation limit")
    premium_daily_translations: int = Field(description="Premium tier daily translation limit")
    free_max_text_length: int = Field(description="Free tier maximum text length for translation")
    premium_max_text_length: int = Field(description="Premium tier maximum text length for translation")
    free_history_retention_days: int = Field(description="Free tier translation history retention in days")
    premium_history_retention_days: int = Field(description="Premium tier translation history retention in days")


class SecurityConfig(BaseModel):
    """Security configuration - only fields used in Python code."""
    sensitive_field_patterns: List[str] = Field(description="Patterns for sensitive field detection")


class ObservabilityConfig(BaseModel):
    """Observability configuration - only fields used in Python code."""
    log_level: LogLevel = Field(description="Log level for the application")
    enable_tracing: bool = Field(description="Whether to enable tracing")


class AppleConfig(BaseModel):
    """Apple configuration for App Store Server API."""
    private_key: str = Field(description="Apple private key (P8 file content)")
    key_id: str = Field(description="Apple Key ID from App Store Connect")
    team_id: str = Field(description="Apple Developer Team ID")
    bundle_id: str = Field(description="App bundle identifier")


class GoogleConfig(BaseModel):
    """Google configuration - only fields used in Python code."""
    service_account_key: str = Field(description="Google service account key for Play Store validation")


class CognitoConfig(BaseModel):
    """Cognito configuration populated by CDK with actual resource IDs."""
    user_pool_id: str = Field(description="Cognito User Pool ID")
    user_pool_client_id: str = Field(description="Cognito App Client ID")
    user_pool_region: str = Field(description="AWS region")
    api_gateway_arn: str = Field(description="API Gateway ARN for authorizer")
