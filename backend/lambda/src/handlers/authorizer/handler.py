"""Lambda authorizer for API Gateway with Cognito JWT validation."""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import jwt
import requests
from jwt.algorithms import RSAAlgorithm

from utils.logging import SmartLogger
from utils.config import AppConfig
from utils.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
)

logger = SmartLogger("api-authorizer")
config = AppConfig()


class CognitoAuthorizer:
    """Cognito JWT token authorizer for API Gateway."""

    def __init__(self) -> None:
        """Initialize the authorizer."""
        self.user_pool_id = os.environ.get("USER_POOL_ID")
        self.user_pool_region = os.environ.get("USER_POOL_REGION", "us-east-1")
        self.api_gateway_arn = os.environ.get("API_GATEWAY_ARN")

        # Cache for JWKS (JSON Web Key Set)
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_cache_time: Optional[datetime] = None
        self._jwks_cache_ttl = 3600  # 1 hour cache

    def _get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set from Cognito."""
        current_time = datetime.now(timezone.utc)

        if (
            self._jwks_cache is not None
            and self._jwks_cache_time is not None
            and (current_time - self._jwks_cache_time).seconds < self._jwks_cache_ttl
        ):
            return self._jwks_cache

        try:
            jwks_url = f"https://cognito-idp.{self.user_pool_region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()

            self._jwks_cache = response.json()
            self._jwks_cache_time = current_time

            return self._jwks_cache
        except Exception as e:
            logger.log_error(
                e, {"operation": "get_jwks", "user_pool_id": self.user_pool_id}
            )
            raise AuthenticationError("Failed to retrieve JWT keys")

    def _get_public_key(self, kid: str) -> str:
        """Get public key for a specific key ID."""
        jwks = self._get_jwks()

        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return RSAAlgorithm.from_jwk(json.dumps(key))

        raise InvalidTokenError(f"JWT key ID '{kid}' not found")

    def _validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return claims."""
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            if not kid:
                raise InvalidTokenError("JWT token missing key ID")

            # Get public key
            public_key = self._get_public_key(kid)

            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.user_pool_id,
                issuer=f"https://cognito-idp.{self.user_pool_region}.amazonaws.com/{self.user_pool_id}",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("JWT token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid JWT token: {str(e)}")
        except Exception as e:
            logger.log_error(e, {"operation": "validate_token"})
            raise AuthenticationError("Token validation failed")

    def _generate_policy(
        self, principal_id: str, effect: str, resource: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate IAM policy for API Gateway."""
        return {
            "principalId": principal_id,
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": effect,
                        "Resource": resource,
                    }
                ],
            },
            "context": context,
        }

    def authorize(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main authorization function for API Gateway.

        Args:
            event: API Gateway authorizer event

        Returns:
            IAM policy document for API Gateway
        """
        try:
            # Extract token from event
            token = event.get("authorizationToken")
            if not token:
                raise InvalidTokenError("No authorization token provided")

            # Remove Bearer prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            # Validate token
            claims = self._validate_token(token)

            # Extract user information
            user_id = claims.get("sub")
            username = claims.get("cognito:username")
            email = claims.get("email")

            if not user_id:
                raise InvalidTokenError("Token missing user ID")

            # Determine user tier/role from claims
            user_tier = claims.get("custom:user_tier", "free")

            # Create context for the policy
            context = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "user_tier": user_tier,
                "token_issued_at": str(claims.get("iat", "")),
                "token_expires_at": str(claims.get("exp", "")),
            }

            # Generate policy
            resource_arn = f"{self.api_gateway_arn}/*"

            logger.log_business_event(
                "authorization_successful",
                {
                    "user_id": user_id,
                    "username": username,
                    "user_tier": user_tier,
                    "method_arn": event.get("methodArn"),
                },
            )

            return self._generate_policy(user_id, "Allow", resource_arn, context)

        except (AuthenticationError, InvalidTokenError, TokenExpiredError) as e:
            logger.log_error(
                e,
                {
                    "operation": "authorize",
                    "method_arn": event.get("methodArn"),
                    "token_length": len(event.get("authorizationToken", "")),
                },
            )

            # Return deny policy
            return self._generate_policy(
                "unauthorized", "Deny", event.get("methodArn", "*"), {"error": str(e)}
            )

        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "authorize",
                    "method_arn": event.get("methodArn"),
                },
            )

            # Return deny policy for unexpected errors
            return self._generate_policy(
                "error",
                "Deny",
                event.get("methodArn", "*"),
                {"error": "Internal authorization error"},
            )


# Global authorizer instance
authorizer = CognitoAuthorizer()


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway authorizer.

    Args:
        event: API Gateway authorizer event
        context: Lambda context

    Returns:
        IAM policy document
    """
    return authorizer.authorize(event)
