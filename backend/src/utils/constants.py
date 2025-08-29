"""Application constants - now using dynamic configuration system."""

from .config import get_config

# Get the configuration instance
config = get_config()


# Backward compatibility exports - these now use the dynamic config
def get_usage_limits():
    """Get usage limits from dynamic configuration."""
    return config.get_usage_limits()


def get_bedrock_model():
    """Get Bedrock model from dynamic configuration."""
    return config.get_bedrock_config()["model"]


def get_bedrock_region():
    """Get Bedrock region from dynamic configuration."""
    return config.get_bedrock_config()["region"]


def get_translation_directions():
    """Get translation directions from dynamic configuration."""
    return config.get_translation_config()["directions"]


def get_table_names():
    """Get table names from dynamic configuration."""
    return config.get_database_config()["tables"]


# Legacy constants for backward compatibility
USAGE_LIMITS = get_usage_limits()
BEDROCK_MODEL = get_bedrock_model()
BEDROCK_REGION = get_bedrock_region()
TRANSLATION_DIRECTIONS = get_translation_directions()
TABLE_NAMES = get_table_names()

# Export the config instance for direct access
__all__ = [
    "config",
    "get_usage_limits",
    "get_bedrock_model",
    "get_bedrock_region",
    "get_translation_directions",
    "get_table_names",
    "USAGE_LIMITS",
    "BEDROCK_MODEL",
    "BEDROCK_REGION",
    "TRANSLATION_DIRECTIONS",
    "TABLE_NAMES",
]
