"""
Pydantic models for Lambda configuration.

These models provide type safety and validation for configuration
loaded from environment variables and secrets.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from models.slang import AgeRating, AgeFilterMode


class LogLevel(str, Enum):
    """Logging level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UsageLimitsConfig(BaseModel):
    """Usage limits configuration."""

    free_daily_translations: int = Field(
        description="Free tier daily translation limit"
    )
    premium_daily_translations: int = Field(
        description="Premium tier daily translation limit"
    )
    free_max_text_length: int = Field(
        description="Free tier maximum text length for translation"
    )
    premium_max_text_length: int = Field(
        description="Premium tier maximum text length for translation"
    )
    free_history_retention_days: int = Field(
        description="Free tier translation history retention in days"
    )
    premium_history_retention_days: int = Field(
        description="Premium tier translation history retention in days"
    )


class SecurityConfig(BaseModel):
    """Security configuration - only fields used in Python code."""

    sensitive_field_patterns: List[str] = Field(
        description="Patterns for sensitive field detection"
    )


class ObservabilityConfig(BaseModel):
    """Observability configuration - only fields used in Python code."""

    log_level: LogLevel = Field(description="Log level for the application")
    enable_tracing: bool = Field(description="Whether to enable tracing")


class AppleConfig(BaseModel):
    """Apple configuration for App Store Server API."""

    private_key: bytes = Field(
        description="Apple private key (P8 file content as bytes)"
    )
    key_id: str = Field(description="Apple Key ID from App Store Connect")
    issuer_id: str = Field(description="Apple Issuer ID (App Store Connect API Key ID)")
    bundle_id: str = Field(description="App bundle identifier")

    @field_validator("private_key", mode="before")
    @classmethod
    def validate_private_key_field(cls, v: str | bytes) -> bytes:
        """Alternative field validator approach - validates Apple private key format and convert to bytes."""
        if not v:
            raise ValueError("Private key cannot be empty")

        # Convert bytes to string for validation if needed
        if isinstance(v, bytes):
            v_str = v.decode("utf-8")
        else:
            v_str = v

        # Validate proper format
        if not v_str.startswith("-----BEGIN PRIVATE KEY-----"):
            raise ValueError(
                "Private key must start with '-----BEGIN PRIVATE KEY-----'"
            )

        if not v_str.endswith("-----END PRIVATE KEY-----"):
            raise ValueError("Private key must end with '-----END PRIVATE KEY-----'")

        # Return as bytes for the Apple SDK
        if isinstance(v, bytes):
            return v
        else:
            return v.encode("utf-8")


class CognitoConfig(BaseModel):
    """Cognito configuration populated by CDK with actual resource IDs."""

    user_pool_id: str = Field(description="Cognito User Pool ID")
    user_pool_client_id: str = Field(description="Cognito App Client ID")
    user_pool_region: str = Field(description="AWS region")
    api_gateway_arn: str = Field(description="API Gateway ARN for authorizer")


class LLMConfig(BaseModel):
    """LLM configuration for translation and trending services."""

    # Lexicon configuration
    lexicon_s3_bucket: str = Field(description="S3 bucket for lexicon")
    lexicon_s3_key: str = Field(description="S3 key for lexicon")
    lexicon_local_path: str = Field(description="Local lexicon path (optional)")

    # LLM configuration
    model: str = Field(description="LLM model ID")
    max_tokens: int = Field(description="Maximum tokens for LLM requests")
    temperature: float = Field(description="Temperature for LLM requests")
    top_p: float = Field(description="Top-p for LLM requests")

    # Age and content filtering
    age_max_rating: AgeRating = Field(description="Maximum age rating")
    age_filter_mode: AgeFilterMode = Field(description="Age filter mode")
