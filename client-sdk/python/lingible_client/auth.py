"""
Lingible API Client Authentication Module

This module provides Cognito authentication and JWT token management
for the Lingible API client SDK.
"""

import json
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

logger = logging.getLogger(__name__)


class CognitoAuthError(Exception):
    """Exception raised for Cognito authentication errors."""
    pass


class TokenExpiredError(Exception):
    """Exception raised when JWT token has expired."""
    pass


class CognitoAuthenticator:
    """
    Handles Cognito authentication and JWT token management.

    This class provides methods to authenticate with AWS Cognito,
    manage JWT tokens, and automatically refresh tokens when they expire.
    """

    def __init__(
        self,
        user_pool_id: str,
        client_id: str,
        region: str = "us-east-1",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize the Cognito authenticator.

        Args:
            user_pool_id: AWS Cognito User Pool ID
            client_id: AWS Cognito User Pool Client ID
            region: AWS region (default: us-east-1)
            username: Username for authentication (optional)
            password: Password for authentication (optional)
        """
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        self.username = username
        self.password = password

        # Initialize Cognito client
        self.cognito_client = boto3.client('cognito-idp', region_name=region)

        # Token storage
        self._access_token: Optional[str] = None
        self._id_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # Auto-authenticate if credentials provided
        if username and password:
            self.authenticate()

    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, str]:
        """
        Authenticate with Cognito and obtain JWT tokens.

        Args:
            username: Username for authentication (optional, uses instance username if not provided)
            password: Password for authentication (optional, uses instance password if not provided)

        Returns:
            Dictionary containing access_token, id_token, and refresh_token

        Raises:
            CognitoAuthError: If authentication fails
        """
        username = username or self.username
        password = password or self.password

        if not username or not password:
            raise CognitoAuthError("Username and password are required for authentication")

        try:
            # Authenticate with Cognito
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )

            auth_result = response['AuthenticationResult']

            # Store tokens
            self._access_token = auth_result['AccessToken']
            self._id_token = auth_result['IdToken']
            self._refresh_token = auth_result.get('RefreshToken')

            # Calculate token expiration
            expires_in = auth_result.get('ExpiresIn', 3600)  # Default to 1 hour
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info(f"Successfully authenticated user: {username}")

            return {
                'access_token': self._access_token,
                'id_token': self._id_token,
                'refresh_token': self._refresh_token
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Cognito authentication failed: {error_code} - {error_message}")
            raise CognitoAuthError(f"Authentication failed: {error_message}")
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            raise CognitoAuthError(f"Authentication failed: {str(e)}")

    def refresh_tokens(self) -> Dict[str, str]:
        """
        Refresh JWT tokens using the refresh token.

        Returns:
            Dictionary containing new access_token, id_token, and refresh_token

        Raises:
            CognitoAuthError: If token refresh fails
            TokenExpiredError: If refresh token is expired
        """
        if not self._refresh_token:
            raise CognitoAuthError("No refresh token available. Please re-authenticate.")

        try:
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': self._refresh_token
                }
            )

            auth_result = response['AuthenticationResult']

            # Update stored tokens
            self._access_token = auth_result['AccessToken']
            self._id_token = auth_result['IdToken']
            self._refresh_token = auth_result.get('RefreshToken', self._refresh_token)

            # Update token expiration
            expires_in = auth_result.get('ExpiresIn', 3600)
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully refreshed JWT tokens")

            return {
                'access_token': self._access_token,
                'id_token': self._id_token,
                'refresh_token': self._refresh_token
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Token refresh failed: {error_code} - {error_message}")

            if error_code == 'NotAuthorizedException':
                raise TokenExpiredError("Refresh token has expired. Please re-authenticate.")
            else:
                raise CognitoAuthError(f"Token refresh failed: {error_message}")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise CognitoAuthError(f"Token refresh failed: {str(e)}")

    def get_valid_token(self) -> str:
        """
        Get a valid JWT token, refreshing if necessary.

        Returns:
            Valid JWT token (access token)

        Raises:
            CognitoAuthError: If no valid token can be obtained
        """
        # Check if we have a token and if it's still valid
        if self._access_token and self._token_expires_at:
            # Add 5 minute buffer to avoid edge cases
            buffer_time = datetime.utcnow() + timedelta(minutes=5)
            if self._token_expires_at > buffer_time:
                return self._access_token

        # Token is expired or doesn't exist, try to refresh
        if self._refresh_token:
            try:
                self.refresh_tokens()
                return self._access_token
            except (TokenExpiredError, CognitoAuthError):
                # Refresh failed, need to re-authenticate
                pass

        # No valid token available, need to re-authenticate
        if self.username and self.password:
            self.authenticate()
            return self._access_token
        else:
            raise CognitoAuthError("No valid token available and no credentials for re-authentication")

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Returns:
            Dictionary containing Authorization header with Bearer token
        """
        token = self.get_valid_token()
        return {
            'Authorization': f'Bearer {token}'
        }

    def decode_token(self, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Decode JWT token to extract claims (without verification).

        Args:
            token: JWT token to decode (uses stored ID token if not provided)

        Returns:
            Dictionary containing token claims

        Raises:
            InvalidTokenError: If token is invalid
        """
        token = token or self._id_token
        if not token:
            raise InvalidTokenError("No token provided")

        try:
            # Decode without verification (for inspection only)
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded
        except Exception as e:
            raise InvalidTokenError(f"Failed to decode token: {str(e)}")

    def get_user_info(self) -> Dict[str, Any]:
        """
        Get user information from the ID token.

        Returns:
            Dictionary containing user information
        """
        if not self._id_token:
            raise CognitoAuthError("No ID token available")

        try:
            claims = self.decode_token(self._id_token)
            return {
                'user_id': claims.get('sub'),
                'email': claims.get('email'),
                'username': claims.get('cognito:username'),
                'email_verified': claims.get('email_verified', False),
                'token_use': claims.get('token_use'),
                'exp': claims.get('exp'),
                'iat': claims.get('iat')
            }
        except InvalidTokenError as e:
            raise CognitoAuthError(f"Failed to get user info: {str(e)}")

    def is_authenticated(self) -> bool:
        """
        Check if the user is currently authenticated with a valid token.

        Returns:
            True if authenticated with valid token, False otherwise
        """
        try:
            self.get_valid_token()
            return True
        except (CognitoAuthError, TokenExpiredError):
            return False

    def logout(self):
        """Clear stored tokens and logout the user."""
        self._access_token = None
        self._id_token = None
        self._refresh_token = None
        self._token_expires_at = None
        logger.info("User logged out successfully")
