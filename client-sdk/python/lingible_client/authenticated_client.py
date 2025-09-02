"""
Authenticated Lingible API Client

This module provides a wrapper around the generated OpenAPI client
that adds Cognito authentication and JWT token management.
"""

import logging
from typing import Optional, Dict, Any

from .auth import CognitoAuthenticator, CognitoAuthError
from .api_client import ApiClient
from .configuration import Configuration
from .api.system_api import SystemApi
from .api.translation_api import TranslationApi
from .api.user_api import UserApi
from .models.translation_request import TranslationRequest
from .models.upgrade_request import UpgradeRequest

logger = logging.getLogger(__name__)


class AuthenticatedLingibleClient:
    """
    Lingible API client with integrated Cognito authentication.

    This client wraps the generated OpenAPI client and adds automatic
    JWT token management for all API calls.
    """

    def __init__(
        self,
        base_url: str,
        user_pool_id: str,
        client_id: str,
        region: str = "us-east-1",
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the authenticated Lingible API client.

        Args:
            base_url: Base URL of the Lingible API
            user_pool_id: AWS Cognito User Pool ID
            client_id: AWS Cognito User Pool Client ID
            region: AWS region (default: us-east-1)
            username: Username for authentication (optional)
            password: Password for authentication (optional)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip('/')

        # Initialize authentication
        self.auth = CognitoAuthenticator(
            user_pool_id=user_pool_id,
            client_id=client_id,
            region=region,
            username=username,
            password=password
        )

        # Setup configuration for the generated client
        self.config = Configuration(
            host=self.base_url
        )

        # Create API client with custom configuration
        self.api_client = ApiClient(self.config)

        # Initialize API classes
        self.system_api = SystemApi(self.api_client)
        self.translation_api = TranslationApi(self.api_client)
        self.user_api = UserApi(self.api_client)

        logger.info(f"Authenticated Lingible client initialized for {base_url}")

    def _add_auth_headers(self):
        """Add authentication headers to the API client."""
        try:
            auth_headers = self.auth.get_auth_headers()
            # Update the default headers in the API client
            for header_name, header_value in auth_headers.items():
                self.api_client.set_default_header(header_name, header_value)
        except CognitoAuthError as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise

    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, str]:
        """
        Authenticate with Cognito and obtain JWT tokens.

        Args:
            username: Username for authentication (optional)
            password: Password for authentication (optional)

        Returns:
            Dictionary containing authentication tokens
        """
        result = self.auth.authenticate(username, password)
        self._add_auth_headers()
        return result

    def is_authenticated(self) -> bool:
        """
        Check if the user is currently authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.auth.is_authenticated()

    def get_user_info(self) -> Dict[str, Any]:
        """
        Get current user information.

        Returns:
            Dictionary containing user information
        """
        return self.auth.get_user_info()

    def logout(self):
        """Logout and clear authentication tokens."""
        self.auth.logout()
        # Clear auth headers
        if 'Authorization' in self.api_client.default_headers:
            del self.api_client.default_headers['Authorization']

    # System API methods
    def health_check(self):
        """
        Check the health status of the API.

        Returns:
            HealthResponse object
        """
        return self.system_api.health_get()

    # Translation API methods
    def translate(
        self,
        text: str,
        direction: str = "english_to_genz"
    ):
        """
        Translate text using the Lingible API.

        Args:
            text: Text to translate
            direction: Translation direction - "english_to_genz" or "genz_to_english"

        Returns:
            TranslationResponse object
        """
        # Ensure we have auth headers
        self._add_auth_headers()

        # Create request object
        request = TranslationRequest(text=text, direction=direction)

        return self.translation_api.translate_post(translation_request=request)

    def get_translation_history(
        self,
        limit: int = 20,
        offset: int = 0
    ):
        """
        Get user's translation history (premium feature).

        Args:
            limit: Number of translations to return (default: 20)
            offset: Number of translations to skip (default: 0)

        Returns:
            TranslationHistoryResponse object
        """
        # Ensure we have auth headers
        self._add_auth_headers()

        return self.translation_api.translations_get(limit=limit, offset=offset)

    def delete_translation(self, translation_id: str):
        """
        Delete a specific translation by ID.

        Args:
            translation_id: ID of the translation to delete

        Returns:
            SuccessResponse object
        """
        # Ensure we have auth headers
        self._add_auth_headers()

        return self.translation_api.translations_translation_id_delete(translation_id=translation_id)

    def delete_all_translations(self):
        """
        Delete all translations for the current user (premium feature).

        Returns:
            SuccessResponse object
        """
        # Ensure we have auth headers
        self._add_auth_headers()

        return self.translation_api.translations_delete_all_delete()

    # User API methods
    def get_user_profile(self):
        """
        Get the current user's profile information.

        Returns:
            UserProfileResponse object
        """
        # Ensure we have auth headers
        self._add_auth_headers()

        return self.user_api.user_profile_get()

    def get_usage_stats(self):
        """
        Get the current user's usage statistics.

        Returns:
            UsageResponse object
        """
        # Ensure we have auth headers
        self._add_auth_headers()

        return self.user_api.user_usage_get()

    def upgrade_subscription(
        self,
        platform: str,
        receipt_data: str
    ):
        """
        Upgrade user to premium subscription.

        Args:
            platform: App store platform ("apple" or "google")
            receipt_data: Receipt data from app store

        Returns:
            UpgradeResponse object
        """
        # Ensure we have auth headers
        self._add_auth_headers()

        # Create request object
        request = UpgradeRequest(platform=platform, receipt_data=receipt_data)

        return self.user_api.user_upgrade_post(upgrade_request=request)


# Convenience functions for common configurations
def create_dev_client(username: str, password: str) -> AuthenticatedLingibleClient:
    """
    Create a client configured for the development environment.

    Args:
        username: Username for authentication
        password: Password for authentication

    Returns:
        Configured AuthenticatedLingibleClient for development
    """
    return AuthenticatedLingibleClient(
        base_url="https://04rie9qo0b.execute-api.us-east-1.amazonaws.com/prod",
        user_pool_id="us-east-1_65YoJgNVi",
        client_id="68n1e6i3fs8m802c5nf5fc94re",
        region="us-east-1",
        username=username,
        password=password
    )


def create_prod_client(username: str, password: str) -> AuthenticatedLingibleClient:
    """
    Create a client configured for the production environment.

    Args:
        username: Username for authentication
        password: Password for authentication

    Returns:
        Configured AuthenticatedLingibleClient for production
    """
    return AuthenticatedLingibleClient(
        base_url="https://api.lingible.com",
        user_pool_id="us-east-1_65YoJgNVi",  # Update with prod values
        client_id="68n1e6i3fs8m802c5nf5fc94re",  # Update with prod values
        region="us-east-1",
        username=username,
        password=password
    )
