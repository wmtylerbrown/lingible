"""AWS services manager for efficient boto3 client initialization."""

import os
import boto3
from typing import Optional, Any
from functools import lru_cache


class AWSServices:
    """Centralized AWS services manager with lazy initialization."""

    def __init__(self) -> None:
        """Initialize AWS services manager."""
        self._cognito_client: Optional[Any] = None
        self._dynamodb_resource: Optional[Any] = None
        self._dynamodb_client: Optional[Any] = None
        self._bedrock_client: Optional[Any] = None
        self._s3_client: Optional[Any] = None

    @property
    def cognito_client(self) -> Any:
        """Get Cognito client (lazy initialization)."""
        if self._cognito_client is None:
            self._cognito_client = boto3.client("cognito-idp")
        return self._cognito_client

    @property
    def dynamodb_resource(self) -> Any:
        """Get DynamoDB resource (lazy initialization)."""
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource("dynamodb")
        return self._dynamodb_resource

    @property
    def dynamodb_client(self) -> Any:
        """Get DynamoDB client (lazy initialization)."""
        if self._dynamodb_client is None:
            self._dynamodb_client = boto3.client("dynamodb")
        return self._dynamodb_client

    @property
    def bedrock_client(self) -> Any:
        """Get Bedrock client (lazy initialization)."""
        if self._bedrock_client is None:
            # Bedrock is only available in specific regions
            region = os.environ.get("AWS_REGION", "us-east-1")
            self._bedrock_client = boto3.client("bedrock-runtime", region_name=region)
        return self._bedrock_client

    @property
    def s3_client(self) -> Any:
        """Get S3 client (lazy initialization)."""
        if self._s3_client is None:
            self._s3_client = boto3.client("s3")
        return self._s3_client

    def get_table(self, table_name: str):
        """Get DynamoDB table instance."""
        return self.dynamodb_resource.Table(table_name)


# Global singleton instance
# This will be initialized once per Lambda container and reused across invocations
aws_services = AWSServices()


# Alternative: Function-based approach for even more explicit control
@lru_cache(maxsize=1)
def get_cognito_client() -> Any:
    """Get Cognito client (cached singleton)."""
    return boto3.client("cognito-idp")


@lru_cache(maxsize=1)
def get_dynamodb_resource() -> Any:
    """Get DynamoDB resource (cached singleton)."""
    return boto3.resource("dynamodb")


@lru_cache(maxsize=1)
def get_dynamodb_client() -> Any:
    """Get DynamoDB client (cached singleton)."""
    return boto3.client("dynamodb")


@lru_cache(maxsize=1)
def get_bedrock_client() -> Any:
    """Get Bedrock client (cached singleton)."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)


@lru_cache(maxsize=1)
def get_s3_client() -> Any:
    """Get S3 client (cached singleton)."""
    return boto3.client("s3")


@lru_cache(maxsize=None)  # Cache all table instances
def get_table(table_name: str):
    """Get DynamoDB table instance (cached by table name)."""
    return get_dynamodb_resource().Table(table_name)
