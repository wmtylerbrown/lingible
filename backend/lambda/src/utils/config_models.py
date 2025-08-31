"""Configuration models for the application."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration model."""
    users_table: str = Field(description="Users table name")
    translations_table: str = Field(description="Translations table name")
    read_capacity: int = Field(default=5, description="DynamoDB read capacity")
    write_capacity: int = Field(default=5, description="DynamoDB write capacity")


class SecurityConfig(BaseModel):
    """Security configuration model."""
    sensitive_fields: List[str] = Field(description="Fields to mask in logs")
    bearer_prefix: str = Field(default="Bearer ", description="Bearer token prefix")
    jwt_expiration: int = Field(default=3600, description="JWT expiration in seconds")
    rate_limiting: Dict[str, Any] = Field(description="Rate limiting configuration")


class APIConfig(BaseModel):
    """API configuration model."""
    cors: Dict[str, Any] = Field(description="CORS configuration")
    pagination: Dict[str, int] = Field(description="Pagination settings")


class MonitoringConfig(BaseModel):
    """Monitoring configuration model."""
    enable_metrics: bool = Field(default=True, description="Enable CloudWatch metrics")
    enable_logging: bool = Field(default=True, description="Enable structured logging")
    enable_tracing: bool = Field(default=True, description="Enable X-Ray tracing")
    log_retention_days: int = Field(default=14, description="CloudWatch log retention")
    metrics_namespace: str = Field(description="CloudWatch metrics namespace")


class TranslationConfig(BaseModel):
    """Translation configuration model."""
    directions: Dict[str, str] = Field(description="Translation direction mappings")
    max_concurrent_translations: int = Field(default=5, description="Max concurrent translations")
    translation_timeout: int = Field(default=30, description="Translation timeout in seconds")


class BedrockConfig(BaseModel):
    """Bedrock configuration model."""
    model: str = Field(description="Bedrock model name")
    region: str = Field(default="us-east-1", description="AWS region")
    max_tokens: int = Field(default=1000, description="Maximum tokens")
    temperature: float = Field(default=0.7, description="Model temperature")


class UsageLimitsConfig(BaseModel):
    """Usage limits configuration model."""
    free: Dict[str, int] = Field(description="Free tier limits")
    premium: Dict[str, int] = Field(description="Premium tier limits")


class AppConfigModel(BaseModel):
    """Complete application configuration model."""
    environment: str = Field(description="Environment name")
    app_name: str = Field(description="Application name")
    database: DatabaseConfig = Field(description="Database configuration")
    security: SecurityConfig = Field(description="Security configuration")
    api: APIConfig = Field(description="API configuration")
    monitoring: MonitoringConfig = Field(description="Monitoring configuration")
    translation: TranslationConfig = Field(description="Translation configuration")
    bedrock: BedrockConfig = Field(description="Bedrock configuration")
    usage_limits: UsageLimitsConfig = Field(description="Usage limits configuration")
