"""
Configuration service for Lambda functions.

This service loads configuration from environment variables and provides
easy access to typed configuration objects.
"""

import json
import os
from typing import Type, TypeVar

from aws_lambda_powertools.utilities.parameters import get_secret
from aws_lambda_powertools import Logger

from models.config import (
    UsageLimitsConfig,
    SecurityConfig,
    ObservabilityConfig,
    AppleConfig,
    CognitoConfig,
    LLMConfig,
    SlangValidationConfig,
    SlangSubmissionConfig,
    QuizConfig,
    LogLevel,
)
from models.slang import AgeRating, AgeFilterMode


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


logger = Logger()

T = TypeVar("T")


class ConfigService:
    """
    Configuration service for Lambda functions.

    Loads configuration from environment variables and provides easy access
    to typed configuration objects.
    """

    def __init__(self):
        self.environment = os.environ["ENVIRONMENT"]  # Required - no default

    def _get_env_var(self, key: str) -> str:
        """
        Get an environment variable value.

        Args:
            key: The environment variable name

        Returns:
            The environment variable value

        Raises:
            ConfigurationError: If environment variable is not set
        """
        try:
            return os.environ[key]
        except KeyError:
            logger.error(f"Required environment variable '{key}' not found")
            raise ConfigurationError(f"Required environment variable '{key}' not found")

    def _get_secrets_manager_secret(self, secret_name: str, key: str) -> str:
        """
        Get a secret from AWS Secrets Manager.

        Args:
            secret_name: The name of the secret in Secrets Manager
            key: The key within the secret JSON

        Returns:
            The secret value

        Raises:
            ConfigurationError: If secret cannot be retrieved
        """
        try:
            # Use Powertools with 5-second TTL for caching
            secret_value = get_secret(secret_name)
            secret_data = json.loads(secret_value)
            return secret_data[key]
        except Exception as e:
            logger.error(f"Failed to retrieve secret '{secret_name}' key '{key}': {e}")
            raise ConfigurationError(
                f"Failed to retrieve secret '{secret_name}' key '{key}': {e}"
            )

    def get_config(self, config_type: Type[T]) -> T:
        """
        Get a typed configuration object.

        Args:
            config_type: The configuration model class

        Returns:
            The configuration object

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        if config_type == UsageLimitsConfig:
            return UsageLimitsConfig(
                free_daily_translations=int(
                    self._get_env_var("FREE_DAILY_TRANSLATIONS")
                ),
                premium_daily_translations=int(
                    self._get_env_var("PREMIUM_DAILY_TRANSLATIONS")
                ),
                free_max_text_length=int(self._get_env_var("FREE_MAX_TEXT_LENGTH")),
                premium_max_text_length=int(
                    self._get_env_var("PREMIUM_MAX_TEXT_LENGTH")
                ),
                free_history_retention_days=int(
                    self._get_env_var("FREE_HISTORY_RETENTION_DAYS")
                ),
                premium_history_retention_days=int(
                    self._get_env_var("PREMIUM_HISTORY_RETENTION_DAYS")
                ),
            )  # type: ignore
        elif config_type == SecurityConfig:
            return SecurityConfig(
                sensitive_field_patterns=json.loads(
                    self._get_env_var("SENSITIVE_FIELD_PATTERNS")
                )
            )  # type: ignore
        elif config_type == ObservabilityConfig:
            return ObservabilityConfig(
                log_level=LogLevel(self._get_env_var("LOG_LEVEL")),
                enable_tracing=self._get_env_var("ENABLE_TRACING").lower() == "true",
            )  # type: ignore
        elif config_type == AppleConfig:
            # Load Apple In-App Purchase credentials from Secrets Manager
            private_key_name = f"lingible-apple-iap-private-key-{self.environment}"

            private_key = self._get_secrets_manager_secret(
                private_key_name, "privateKey"
            )

            # Get Apple credentials from environment variables (set by CDK)
            key_id = self._get_env_var("APPLE_KEY_ID")
            issuer_id = self._get_env_var("APPLE_ISSUER_ID")
            bundle_id = self._get_env_var("APPLE_BUNDLE_ID")

            return AppleConfig(
                private_key=private_key,  # type: ignore[arg-type] # Pydantic validator converts str -> bytes
                key_id=key_id,
                issuer_id=issuer_id,
                bundle_id=bundle_id,
            )  # type: ignore
        elif config_type == CognitoConfig:
            return CognitoConfig(
                user_pool_id=self._get_env_var("COGNITO_USER_POOL_ID"),
                user_pool_client_id=self._get_env_var("COGNITO_USER_POOL_CLIENT_ID"),
                user_pool_region=self._get_env_var("COGNITO_USER_POOL_REGION"),
                api_gateway_arn=self._get_env_var("API_GATEWAY_ARN"),
            )  # type: ignore
        elif config_type == LLMConfig:
            return LLMConfig(
                lexicon_s3_bucket=self._get_env_var("LEXICON_S3_BUCKET"),
                lexicon_s3_key=self._get_env_var("LEXICON_S3_KEY"),
                model=self._get_env_var("LLM_MODEL_ID"),
                max_tokens=int(self._get_env_var("LLM_MAX_TOKENS")),
                temperature=float(self._get_env_var("LLM_TEMPERATURE")),
                top_p=float(self._get_env_var("LLM_TOP_P")),
                age_max_rating=AgeRating(self._get_env_var("AGE_MAX_RATING")),
                age_filter_mode=AgeFilterMode(self._get_env_var("AGE_FILTER_MODE")),
                low_confidence_threshold=float(
                    self._get_env_var("LLM_LOW_CONFIDENCE_THRESHOLD")
                ),
            )  # type: ignore
        elif config_type == SlangValidationConfig:
            # Try to get Tavily API key from Secrets Manager
            tavily_api_key = ""
            try:
                secret_name = f"lingible-tavily-api-key-{self.environment}"
                tavily_api_key = self._get_secrets_manager_secret(secret_name, "apiKey")
            except Exception as e:
                # Log but don't fail - validation will work without web search
                logger.debug(f"Tavily API key not found, web search disabled: {e}")

            return SlangValidationConfig(
                auto_approval_enabled=(
                    self._get_env_var("SLANG_VALIDATION_AUTO_APPROVAL_ENABLED").lower()
                    == "true"
                ),
                auto_approval_threshold=float(
                    self._get_env_var("SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD")
                ),
                web_search_enabled=(
                    self._get_env_var("SLANG_VALIDATION_WEB_SEARCH_ENABLED").lower()
                    == "true"
                ),
                max_search_results=int(
                    self._get_env_var("SLANG_VALIDATION_MAX_SEARCH_RESULTS")
                ),
                tavily_api_key=tavily_api_key,
            )  # type: ignore
        elif config_type == SlangSubmissionConfig:
            return SlangSubmissionConfig(
                submissions_topic_arn=self._get_env_var("SLANG_SUBMISSIONS_TOPIC_ARN"),
                validation_request_topic_arn=self._get_env_var(
                    "SLANG_VALIDATION_REQUEST_TOPIC_ARN"
                ),
            )  # type: ignore
        elif config_type == QuizConfig:
            return QuizConfig(
                free_daily_limit=int(self._get_env_var("QUIZ_FREE_DAILY_LIMIT")),
                premium_unlimited=True,
                questions_per_quiz=int(self._get_env_var("QUIZ_QUESTIONS_PER_QUIZ")),
                time_limit_seconds=int(self._get_env_var("QUIZ_TIME_LIMIT_SECONDS")),
                points_per_correct=10,
                enable_time_bonus=True,
            )  # type: ignore
        else:
            raise ConfigurationError(f"Unknown configuration type: {config_type}")


# Global config service instance
_config_service: ConfigService | None = None


def get_config_service() -> ConfigService:
    """Get the global config service instance."""
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
