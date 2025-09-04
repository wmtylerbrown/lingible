"""
Pydantic models for Lambda configuration.

These models provide type safety and validation for configuration
loaded from SSM Parameter Store.
"""

from typing import List
from pydantic import BaseModel, Field, validator
from enum import Enum
from .subscriptions import StoreEnvironment


# Enums for validation
class LogLevel(str, Enum):
    """Logging level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Configuration models used by config service
class BedrockModel(BaseModel):
    """Bedrock configuration."""
    model: str = Field(description="Required: Bedrock model ID")
    region: str = Field(description="Required: AWS region for Bedrock")
    max_tokens: int = Field(default=1000, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @validator('model')
    def validate_model(cls, v):
        if not v or not v.strip():
            raise ValueError("Bedrock model is required and cannot be empty")
        return v


class TableConfigModel(BaseModel):
    """Database table configuration."""
    name: str = Field(description="Required: DynamoDB table name")
    read_capacity: int = Field(default=5, ge=1)
    write_capacity: int = Field(default=5, ge=1)

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Table name is required and cannot be empty")
        return v


class LimitsModel(BaseModel):
    """Usage limits configuration."""
    free_daily_translations: int = 10
    free_max_text_length: int = 50
    free_history_retention_days: int = 0
    premium_daily_translations: int = 100
    premium_max_text_length: int = 100
    premium_history_retention_days: int = 30


class TranslationModel(BaseModel):
    """Translation configuration."""
    context: str = "GenZ slang to formal English and vice versa"
    max_concurrent: int = 5
    timeout_seconds: int = 30


class SecurityModel(BaseModel):
    """Security configuration."""
    sensitive_field_patterns: List[str] = ["*token*", "*secret*", "*key*", "*auth*"]
    bearer_prefix: str = "Bearer "
    jwt_expiration_seconds: int = 7200  # 2 hours


class ObservabilityModel(BaseModel):
    """Observability configuration."""
    debug_mode: bool = True
    log_level: LogLevel = LogLevel.DEBUG
    enable_metrics: bool = False
    enable_tracing: bool = True
    log_retention_days: int = 7


class AppleModel(BaseModel):
    """Apple configuration."""
    client_id: str  # Required - no default
    team_id: str = ""
    key_id: str = ""
    bundle_id: str = ""
    environment: StoreEnvironment = StoreEnvironment.SANDBOX
    shared_secret: str = ""


class GoogleModel(BaseModel):
    """Google configuration."""
    package_name: str  # Required - no default
    service_account_key: str = ""  # Path to service account key file


class CognitoModel(BaseModel):
    """Cognito configuration populated by CDK with actual resource IDs."""
    user_pool_id: str  # Required - populated by CDK
    user_pool_client_id: str  # Required - populated by CDK
    user_pool_region: str  # Required - populated by CDK
    api_gateway_arn: str  # Required - populated by CDK
