"""
Configuration service for Lambda functions.

This service loads configuration from SSM Parameter Store and provides
easy access to typed configuration objects.
"""

import json
import os
from typing import Dict, Any, Optional, TypeVar, Type

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter, get_secret

# Import the Pydantic models we defined
from models.config import (
    BedrockModel as BedrockConfig,
    TableConfigModel as TableConfig,
    LimitsModel as UsageLimitsConfig,
    TranslationModel as TranslationConfig,
    SecurityModel as SecurityConfig,
    ObservabilityModel as ObservabilityConfig,
    AppleModel as AppleConfig,
    GoogleModel as GoogleConfig,
    CognitoModel as CognitoConfig,
)

logger = Logger()

# Type variable for generic config loading
T = TypeVar('T')


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigService:
    """
    Configuration service for Lambda functions.

    Loads configuration from SSM Parameter Store and provides easy access
    to typed configuration objects.
    """

    # Mapping of config types to their SSM parameter names
    # For table configs, we use a tuple: (parameter_name, default_name_template)
    CONFIG_MAPPING = {
        BedrockConfig: "bedrock",
        UsageLimitsConfig: "limits",
        TranslationConfig: "translation",
        SecurityConfig: "security",
        ObservabilityConfig: "observability",
        AppleConfig: "apple",
        GoogleConfig: "google",
        CognitoConfig: "cognito",
    }

    # Special table config mappings
    TABLE_CONFIG_MAPPING = {
        "users": ("users_table", "lingible-users-{environment}"),
        "translations": ("translations_table", "lingible-translations-{environment}"),
        "trending": ("trending_table", "lingible-trending-{environment}"),
    }

    def __init__(self):
        self.app_name = "lingible"  # Fixed app name
        self.environment = os.environ["ENVIRONMENT"]  # Required - no default
        self.parameter_prefix = f"/{self.app_name}/{self.environment}"

    def _get_ssm_parameter(self, parameter_name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a configuration section from SSM Parameter Store.

        Args:
            parameter_name: The parameter name (without prefix)
            default: Default value if parameter doesn't exist

        Returns:
            Parsed JSON configuration

        Raises:
            ConfigurationError: If parameter doesn't exist and no default provided
        """
        full_parameter_name = f"{self.parameter_prefix}/{parameter_name}"

        try:
            # Get from SSM Parameter Store using Powertools built-in caching (5 minutes default)
            # No additional caching needed - Powertools handles this efficiently
            value = get_parameter(full_parameter_name, decrypt=True)
            return json.loads(value)
        except Exception as e:
            if default is not None:
                logger.warning(f"Failed to load parameter {full_parameter_name}, using default: {str(e)}")
                return default

            logger.error(f"Failed to load configuration parameter {full_parameter_name}: {str(e)}")
            raise ConfigurationError(f"Configuration parameter '{parameter_name}' not found: {str(e)}")

    def _get_secrets_manager_secret(self, secret_name: str, key: str) -> str:
        """
        Get a secret value from AWS Secrets Manager using Powertools.

        This method provides a generic way to load secrets from AWS Secrets Manager
        with built-in caching (5 minutes) and proper error handling.

        Args:
            secret_name: The name of the secret in Secrets Manager
            key: The key within the secret JSON to retrieve

        Returns:
            Secret value string

        Raises:
            ConfigurationError: If secret cannot be loaded

        Example:
            # Load Apple shared secret
            shared_secret = self._get_secrets_manager_secret(
                "lingible-apple-shared-secret-dev", 
                "sharedSecret"
            )
            
            # Load Google service account key
            service_key = self._get_secrets_manager_secret(
                "lingible-google-service-account-dev",
                "private_key"
            )
        """
        try:
            # Use Powertools get_secret with built-in caching (5 minutes default)
            secret_data = get_secret(secret_name)
            if isinstance(secret_data, str):
                # If it's a string, try to parse as JSON
                secret_data = json.loads(secret_data)
            
            if not isinstance(secret_data, dict):
                raise ConfigurationError(f"Secret '{secret_name}' is not a valid JSON object")
            
            if key not in secret_data:
                raise ConfigurationError(f"Key '{key}' not found in secret '{secret_name}'")
            
            return str(secret_data[key])
        except Exception as e:
            logger.error(f"Failed to load secret '{secret_name}' key '{key}': {str(e)}")
            raise ConfigurationError(f"Secret '{secret_name}' key '{key}' not found: {str(e)}")

    def get_config(self, config_type: Type[T], table_name: Optional[str] = None) -> T:
        """
        Get configuration of the specified type.

        Args:
            config_type: The configuration class type to load
            table_name: For TableConfig, specify which table ("users" or "translations")

        Returns:
            Instance of the requested configuration type

        Example:
            bedrock = config.get_config(BedrockConfig)
            limits = config.get_config(UsageLimitsConfig)
            users_table = config.get_config(TableConfig, "users")
            translations_table = config.get_config(TableConfig, "translations")
        """
        # Handle table configs specially
        if config_type == TableConfig:
            if table_name is None:
                raise ConfigurationError("table_name is required when getting TableConfig")

            if table_name not in self.TABLE_CONFIG_MAPPING:
                raise ConfigurationError(f"Unknown table name: {table_name}. Available: {list(self.TABLE_CONFIG_MAPPING.keys())}")

            parameter_name, default_name_template = self.TABLE_CONFIG_MAPPING[table_name]
            table_data = self._get_ssm_parameter(parameter_name, {})

            # Apply default name if not specified
            if "name" not in table_data:
                table_data["name"] = default_name_template.format(environment=self.environment)

            return config_type(**table_data)  # type: ignore

        # Handle regular configs
        parameter_name = self.CONFIG_MAPPING.get(config_type)  # type: ignore

        if parameter_name is None:
            raise ConfigurationError(f"Unknown config type: {config_type}")

        config_data = self._get_ssm_parameter(parameter_name, {})

        # Add special environment-based defaults for certain configs
        if config_type == ObservabilityConfig:
            # Apply environment-specific defaults
            if "debug_mode" not in config_data:
                config_data["debug_mode"] = self.environment != "prod"
            if "log_level" not in config_data:
                config_data["log_level"] = "INFO" if self.environment == "prod" else "DEBUG"
            if "enable_metrics" not in config_data:
                config_data["enable_metrics"] = self.environment == "prod"
            if "log_retention_days" not in config_data:
                config_data["log_retention_days"] = 30 if self.environment == "prod" else 7
        elif config_type == AppleConfig:
            # Load shared secret from Secrets Manager
            try:
                secret_name = f"lingible-apple-shared-secret-{self.environment}"
                config_data["shared_secret"] = self._get_secrets_manager_secret(secret_name, "sharedSecret")
            except ConfigurationError:
                # Fallback to empty string if secret not found (for backward compatibility)
                logger.warning("Apple shared secret not found in Secrets Manager, using empty string")
                config_data["shared_secret"] = ""

        return config_type(**config_data)



    # Raw configuration access (for backward compatibility)
    def get_raw_config(self, section: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get raw configuration section."""
        return self._get_ssm_parameter(section, default or {})

    def clear_cache(self):
        """
        Clear the configuration cache. Useful for testing.

        Note: This service relies on AWS Lambda Powertools caching,
        which automatically expires after 5 minutes. For immediate
        cache clearing in tests, you may need to restart the Lambda
        function or use Powertools' cache clearing mechanisms.
        """
        # Powertools handles caching internally - no manual clearing needed
        logger.info("Config cache clear requested - relying on Powertools cache expiration")


# Global configuration service instance
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    Get the global configuration service instance.

    Returns:
        ConfigService instance
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service


# Usage pattern:
# from utils.config import get_config_service, BedrockConfig, UsageLimitsConfig, TableConfig
# config = get_config_service()
#
# # Generic method for most configs
# bedrock = config.get_config(BedrockConfig)
# limits = config.get_config(UsageLimitsConfig)
# security = config.get_config(SecurityConfig)
#
# # Table configs with table name parameter
# users_table = config.get_config(TableConfig, "users")
# translations_table = config.get_config(TableConfig, "translations")
#
# # Use the validated models with defaults and validation
# model = bedrock.model  # Required field, will fail if missing
# max_tokens = bedrock.max_tokens  # Has default of 1000
