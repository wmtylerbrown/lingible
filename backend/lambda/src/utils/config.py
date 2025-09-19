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
    BedrockConfig,
    UsageLimitsConfig,
    SecurityConfig,
    ObservabilityConfig,
    AppleConfig,
    GoogleConfig,
    CognitoConfig,
)

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass

logger = Logger()

T = TypeVar('T')


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
            raise ConfigurationError(f"Failed to retrieve secret '{secret_name}' key '{key}': {e}")

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
        if config_type == BedrockConfig:
            return BedrockConfig(
                model=self._get_env_var('BEDROCK_MODEL'),
                max_tokens=int(self._get_env_var('BEDROCK_MAX_TOKENS')),
                temperature=float(self._get_env_var('BEDROCK_TEMPERATURE'))
            )  # type: ignore
        elif config_type == UsageLimitsConfig:
            return UsageLimitsConfig(
                free_daily_translations=int(self._get_env_var('FREE_DAILY_TRANSLATIONS')),
                premium_daily_translations=int(self._get_env_var('PREMIUM_DAILY_TRANSLATIONS')),
                free_max_text_length=int(self._get_env_var('FREE_MAX_TEXT_LENGTH')),
                premium_max_text_length=int(self._get_env_var('PREMIUM_MAX_TEXT_LENGTH')),
                free_history_retention_days=int(self._get_env_var('FREE_HISTORY_RETENTION_DAYS')),
                premium_history_retention_days=int(self._get_env_var('PREMIUM_HISTORY_RETENTION_DAYS'))
            )  # type: ignore
        elif config_type == SecurityConfig:
            return SecurityConfig(
                sensitive_field_patterns=json.loads(self._get_env_var('SENSITIVE_FIELD_PATTERNS'))
            )  # type: ignore
        elif config_type == ObservabilityConfig:
            from models.config import LogLevel
            return ObservabilityConfig(
                log_level=LogLevel(self._get_env_var('LOG_LEVEL')),
                enable_tracing=self._get_env_var('ENABLE_TRACING').lower() == 'true'
            )  # type: ignore
        elif config_type == AppleConfig:
            # Load Apple credentials from Secrets Manager
            private_key_name = f"lingible-apple-private-key-{self.environment}"

            private_key = self._get_secrets_manager_secret(private_key_name, "privateKey")

            # Get Apple credentials from environment variables (set by CDK)
            key_id = self._get_env_var('APPLE_KEY_ID')
            team_id = self._get_env_var('APPLE_TEAM_ID')
            bundle_id = self._get_env_var('APPLE_BUNDLE_ID')

            return AppleConfig(
                private_key=private_key,
                key_id=key_id,
                team_id=team_id,
                bundle_id=bundle_id
            )  # type: ignore
        elif config_type == GoogleConfig:
            # Load service account key from Secrets Manager
            secret_name = f"lingible-google-service-account-{self.environment}"
            service_account_key = self._get_secrets_manager_secret(secret_name, "private_key")

            return GoogleConfig(
                service_account_key=service_account_key
            )  # type: ignore
        elif config_type == CognitoConfig:
            return CognitoConfig(
                user_pool_id=self._get_env_var('COGNITO_USER_POOL_ID'),
                user_pool_client_id=self._get_env_var('COGNITO_USER_POOL_CLIENT_ID'),
                user_pool_region=self._get_env_var('COGNITO_USER_POOL_REGION'),
                api_gateway_arn=self._get_env_var('API_GATEWAY_ARN')
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
