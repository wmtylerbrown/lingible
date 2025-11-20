from __future__ import annotations

"""Shared fixtures for the repository/service test suite."""

import os
from collections.abc import Iterator
from typing import Any, Generator

import boto3  # type: ignore[import]
import pytest
from moto import mock_aws  # type: ignore[import]

from utils.aws_services import aws_services  # type: ignore[import]
from utils import config as config_module  # type: ignore[import]


def pytest_configure(config: pytest.Config) -> None:  # type: ignore[override]
    """Ensure critical env vars exist before repository modules import."""
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "fake")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "fake")
    os.environ.setdefault("AWS_SESSION_TOKEN", "fake")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("ENABLE_TRACING", "false")
    os.environ.setdefault("ENABLE_METRICS", "false")
    os.environ.setdefault("APP_NAME", "lingible-backend-tests")
    # Set default table names for handlers that initialize at module level
    os.environ.setdefault("USERS_TABLE", "test-users-table")
    os.environ.setdefault("TRANSLATIONS_TABLE", "test-translations-table")
    os.environ.setdefault("TERMS_TABLE", "test-terms-table")
    os.environ.setdefault("SUBMISSIONS_TABLE", "test-submissions-table")
    os.environ.setdefault("LEXICON_TABLE", "test-lexicon-table")
    os.environ.setdefault("TRENDING_TABLE", "test-trending-table")
    # Set default configuration environment variables
    os.environ.setdefault("FREE_DAILY_TRANSLATIONS", "10")
    os.environ.setdefault("PREMIUM_DAILY_TRANSLATIONS", "100")
    os.environ.setdefault("FREE_MAX_TEXT_LENGTH", "100")
    os.environ.setdefault("PREMIUM_MAX_TEXT_LENGTH", "500")
    os.environ.setdefault("FREE_HISTORY_RETENTION_DAYS", "7")
    os.environ.setdefault("PREMIUM_HISTORY_RETENTION_DAYS", "90")
    os.environ.setdefault("SENSITIVE_FIELD_PATTERNS", '["authorization","cookie"]')
    # LLM configuration
    os.environ.setdefault("LEXICON_S3_BUCKET", "test-lexicon-bucket")
    os.environ.setdefault("LEXICON_S3_KEY", "lexicon.json")
    os.environ.setdefault("LLM_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    os.environ.setdefault("LLM_MAX_TOKENS", "4000")
    os.environ.setdefault("LLM_TEMPERATURE", "0.7")
    os.environ.setdefault("LLM_TOP_P", "0.9")
    os.environ.setdefault("LLM_LOW_CONFIDENCE_THRESHOLD", "0.3")
    os.environ.setdefault("AGE_MAX_RATING", "M18")
    os.environ.setdefault("AGE_FILTER_MODE", "skip")
    # Slang validation configuration
    os.environ.setdefault("SLANG_VALIDATION_AUTO_APPROVAL_ENABLED", "true")
    os.environ.setdefault("SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD", "0.85")
    os.environ.setdefault("SLANG_VALIDATION_WEB_SEARCH_ENABLED", "false")
    os.environ.setdefault("SLANG_VALIDATION_MAX_SEARCH_RESULTS", "3")
    os.environ.setdefault("SLANG_SUBMISSIONS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:submissions")
    os.environ.setdefault("SLANG_VALIDATION_REQUEST_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:validation")
    # Quiz configuration
    os.environ.setdefault("QUIZ_FREE_DAILY_LIMIT", "3")
    os.environ.setdefault("QUIZ_PREMIUM_UNLIMITED", "false")
    os.environ.setdefault("QUIZ_QUESTIONS_PER_QUIZ", "10")
    os.environ.setdefault("QUIZ_TIME_LIMIT_SECONDS", "60")
    os.environ.setdefault("QUIZ_POINTS_PER_CORRECT", "10")
    os.environ.setdefault("QUIZ_ENABLE_TIME_BONUS", "true")
    # Cognito configuration (may be needed by some handlers)
    os.environ.setdefault("COGNITO_USER_POOL_ID", "test-pool-id")
    os.environ.setdefault("COGNITO_USER_POOL_CLIENT_ID", "test-client-id")
    os.environ.setdefault("COGNITO_USER_POOL_REGION", "us-east-1")
    os.environ.setdefault("API_GATEWAY_ARN", "arn:aws:apigateway:us-east-1:123456789012:restapi/test")
    # Apple configuration (may be needed by some handlers)
    os.environ.setdefault("APPLE_KEY_ID", "test-key-id")
    os.environ.setdefault("APPLE_ISSUER_ID", "test-issuer-id")
    os.environ.setdefault("APPLE_BUNDLE_ID", "com.lingible.lingible")


@pytest.fixture(scope="session", autouse=True)
def configure_base_environment() -> Generator[None, None, None]:
    """Configure core environment variables required by config service."""

    original_env = os.environ.copy()

    try:
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "fake")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "fake")
        os.environ.setdefault("AWS_SESSION_TOKEN", "fake")
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        os.environ.setdefault("ENVIRONMENT", "test")
        os.environ.setdefault("LOG_LEVEL", "INFO")
        os.environ.setdefault("ENABLE_TRACING", "false")
        os.environ.setdefault("ENABLE_METRICS", "false")
        os.environ.setdefault("APP_NAME", "lingible-backend-tests")
        # Set default table names for handlers that initialize at module level
        os.environ.setdefault("USERS_TABLE", "test-users-table")
        os.environ.setdefault("TRANSLATIONS_TABLE", "test-translations-table")
        os.environ.setdefault("TERMS_TABLE", "test-terms-table")
        os.environ.setdefault("SUBMISSIONS_TABLE", "test-submissions-table")
        os.environ.setdefault("LEXICON_TABLE", "test-lexicon-table")
        os.environ.setdefault("TRENDING_TABLE", "test-trending-table")
        # Set default configuration environment variables
        os.environ.setdefault("FREE_DAILY_TRANSLATIONS", "10")
        os.environ.setdefault("PREMIUM_DAILY_TRANSLATIONS", "100")
        os.environ.setdefault("FREE_MAX_TEXT_LENGTH", "100")
        os.environ.setdefault("PREMIUM_MAX_TEXT_LENGTH", "500")
        os.environ.setdefault("FREE_HISTORY_RETENTION_DAYS", "7")
        os.environ.setdefault("PREMIUM_HISTORY_RETENTION_DAYS", "90")
        os.environ.setdefault("SENSITIVE_FIELD_PATTERNS", '["authorization","cookie"]')
        # LLM configuration
        os.environ.setdefault("LEXICON_S3_BUCKET", "test-lexicon-bucket")
        os.environ.setdefault("LEXICON_S3_KEY", "lexicon.json")
        os.environ.setdefault("LLM_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        os.environ.setdefault("LLM_MAX_TOKENS", "4000")
        os.environ.setdefault("LLM_TEMPERATURE", "0.7")
        os.environ.setdefault("LLM_TOP_P", "0.9")
        os.environ.setdefault("LLM_LOW_CONFIDENCE_THRESHOLD", "0.3")
        os.environ.setdefault("AGE_MAX_RATING", "M18")
        os.environ.setdefault("AGE_FILTER_MODE", "skip")
        # Slang validation configuration
        os.environ.setdefault("SLANG_VALIDATION_AUTO_APPROVAL_ENABLED", "true")
        os.environ.setdefault("SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD", "0.85")
        os.environ.setdefault("SLANG_VALIDATION_WEB_SEARCH_ENABLED", "false")
        os.environ.setdefault("SLANG_VALIDATION_MAX_SEARCH_RESULTS", "3")
        os.environ.setdefault("SLANG_SUBMISSIONS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:submissions")
        os.environ.setdefault("SLANG_VALIDATION_REQUEST_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:validation")
        # Quiz configuration
        os.environ.setdefault("QUIZ_FREE_DAILY_LIMIT", "3")
        os.environ.setdefault("QUIZ_PREMIUM_UNLIMITED", "false")
        os.environ.setdefault("QUIZ_QUESTIONS_PER_QUIZ", "10")
        os.environ.setdefault("QUIZ_TIME_LIMIT_SECONDS", "60")
        os.environ.setdefault("QUIZ_POINTS_PER_CORRECT", "10")
        os.environ.setdefault("QUIZ_ENABLE_TIME_BONUS", "true")
        # Cognito configuration (may be needed by some handlers)
        os.environ.setdefault("COGNITO_USER_POOL_ID", "test-pool-id")
        os.environ.setdefault("COGNITO_USER_POOL_CLIENT_ID", "test-client-id")
        os.environ.setdefault("COGNITO_USER_POOL_REGION", "us-east-1")
        os.environ.setdefault("API_GATEWAY_ARN", "arn:aws:apigateway:us-east-1:123456789012:restapi/test")
        # Apple configuration (may be needed by some handlers)
        os.environ.setdefault("APPLE_KEY_ID", "test-key-id")
        os.environ.setdefault("APPLE_ISSUER_ID", "test-issuer-id")
        os.environ.setdefault("APPLE_BUNDLE_ID", "com.lingible.lingible")

        yield
    finally:
        # Restore the original environment to avoid cross-suite pollution
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def moto_dynamodb() -> Iterator[Any]:
    """Provide a moto-backed DynamoDB resource and reset AWS service caches."""

    with mock_aws():
        resource = boto3.resource("dynamodb", region_name="us-east-1")

        # Reset cached boto3 clients on the shared aws_services singleton so it
        # uses the moto resource created above for the lifetime of this fixture.
        aws_services._dynamodb_resource = None  # type: ignore[attr-defined]
        aws_services._dynamodb_client = None  # type: ignore[attr-defined]

        yield resource


@pytest.fixture
def translations_table(moto_dynamodb: Any) -> str:
    """Create the translations table structure expected by TranslationRepository."""

    table_name = "test-translations-table"
    os.environ["TRANSLATIONS_TABLE"] = table_name

    # Ensure the global config service picks up the freshly set environment.
    config_module._config_service = None  # type: ignore[attr-defined]

    moto_dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Prime aws_services with the moto resource so repository lookups resolve correctly.
    aws_services._dynamodb_resource = moto_dynamodb  # type: ignore[attr-defined]
    aws_services._dynamodb_client = moto_dynamodb.meta.client  # type: ignore[attr-defined]

    return table_name


@pytest.fixture
def users_table(moto_dynamodb: Any) -> str:
    """Create the users table schema expected by UserRepository."""

    table_name = "test-users-table"
    os.environ["USERS_TABLE"] = table_name
    config_module._config_service = None  # type: ignore[attr-defined]

    moto_dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    aws_services._dynamodb_resource = moto_dynamodb  # type: ignore[attr-defined]
    aws_services._dynamodb_client = moto_dynamodb.meta.client  # type: ignore[attr-defined]

    return table_name


def _create_table(
    moto_dynamodb: Any,
    *,
    table_name: str,
    attribute_definitions: list[dict[str, str]],
    key_schema: list[dict[str, str]],
    global_secondary_indexes: list[dict[str, Any]] | None = None,
) -> None:
    kwargs: dict[str, Any] = {
        "TableName": table_name,
        "KeySchema": key_schema,
        "AttributeDefinitions": attribute_definitions,
        "BillingMode": "PAY_PER_REQUEST",
    }
    if global_secondary_indexes:
        kwargs["GlobalSecondaryIndexes"] = global_secondary_indexes
    moto_dynamodb.create_table(**kwargs)


@pytest.fixture
def submissions_table(moto_dynamodb: Any) -> str:
    """Create the submissions table schema used by SubmissionsRepository."""

    table_name = "test-submissions-table"
    os.environ["SUBMISSIONS_TABLE"] = table_name
    config_module._config_service = None  # type: ignore[attr-defined]

    attribute_definitions = [
        {"AttributeName": "PK", "AttributeType": "S"},
        {"AttributeName": "SK", "AttributeType": "S"},
        {"AttributeName": "status", "AttributeType": "S"},
        {"AttributeName": "status_created_at", "AttributeType": "S"},
        {"AttributeName": "user_id", "AttributeType": "S"},
        {"AttributeName": "user_created_at", "AttributeType": "S"},
        {"AttributeName": "submission_id", "AttributeType": "S"},
        {"AttributeName": "llm_validation_status", "AttributeType": "S"},
    ]
    global_secondary_indexes = [
        {
            "IndexName": "SubmissionsStatusIndex",
            "KeySchema": [
                {"AttributeName": "status", "KeyType": "HASH"},
                {"AttributeName": "status_created_at", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["submission_id", "user_id", "slang_term", "context"]},
        },
        {
            "IndexName": "SubmissionsByUserIndex",
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "user_created_at", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "KEYS_ONLY"},
        },
        {
            "IndexName": "SubmissionsByIdIndex",
            "KeySchema": [
                {"AttributeName": "submission_id", "KeyType": "HASH"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        },
        {
            "IndexName": "ValidationStatusIndex",
            "KeySchema": [
                {"AttributeName": "llm_validation_status", "KeyType": "HASH"},
            ],
            "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["submission_id", "user_id", "slang_term"]},
        },
    ]

    _create_table(
        moto_dynamodb,
        table_name=table_name,
        attribute_definitions=attribute_definitions,
        key_schema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        global_secondary_indexes=global_secondary_indexes,
    )

    aws_services._dynamodb_resource = moto_dynamodb  # type: ignore[attr-defined]
    aws_services._dynamodb_client = moto_dynamodb.meta.client  # type: ignore[attr-defined]
    return table_name


@pytest.fixture
def lexicon_table(moto_dynamodb: Any) -> str:
    """Create the lexicon table schema used by LexiconRepository."""

    table_name = "test-lexicon-table"
    os.environ["LEXICON_TABLE"] = table_name
    config_module._config_service = None  # type: ignore[attr-defined]

    attribute_definitions = [
        {"AttributeName": "PK", "AttributeType": "S"},
        {"AttributeName": "SK", "AttributeType": "S"},
        {"AttributeName": "source", "AttributeType": "S"},
        {"AttributeName": "term", "AttributeType": "S"},
        {"AttributeName": "quiz_difficulty", "AttributeType": "S"},
        {"AttributeName": "quiz_category", "AttributeType": "S"},
        {"AttributeName": "quiz_score", "AttributeType": "N"},
    ]
    global_secondary_indexes = [
        {
            "IndexName": "LexiconSourceIndex",
            "KeySchema": [
                {"AttributeName": "source", "KeyType": "HASH"},
                {"AttributeName": "term", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "KEYS_ONLY"},
        },
        {
            "IndexName": "LexiconQuizDifficultyIndex",
            "KeySchema": [
                {"AttributeName": "quiz_difficulty", "KeyType": "HASH"},
                {"AttributeName": "quiz_score", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["term", "gloss", "examples", "tags", "is_quiz_eligible"]},
        },
        {
            "IndexName": "LexiconQuizCategoryIndex",
            "KeySchema": [
                {"AttributeName": "quiz_category", "KeyType": "HASH"},
                {"AttributeName": "quiz_score", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["term", "gloss", "examples", "tags", "is_quiz_eligible"]},
        },
    ]

    _create_table(
        moto_dynamodb,
        table_name=table_name,
        attribute_definitions=attribute_definitions,
        key_schema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        global_secondary_indexes=global_secondary_indexes,
    )

    aws_services._dynamodb_resource = moto_dynamodb  # type: ignore[attr-defined]
    aws_services._dynamodb_client = moto_dynamodb.meta.client  # type: ignore[attr-defined]
    return table_name


@pytest.fixture
def trending_table(moto_dynamodb: Any) -> str:
    """Create the trending table schema used by TrendingRepository."""

    table_name = "test-trending-table"
    os.environ["TRENDING_TABLE"] = table_name
    config_module._config_service = None  # type: ignore[attr-defined]

    attribute_definitions = [
        {"AttributeName": "PK", "AttributeType": "S"},
        {"AttributeName": "SK", "AttributeType": "S"},
        {"AttributeName": "is_active", "AttributeType": "S"},
        {"AttributeName": "category", "AttributeType": "S"},
        {"AttributeName": "popularity_score", "AttributeType": "N"},
    ]
    global_secondary_indexes = [
        {
            "IndexName": "TrendingActiveIndex",
            "KeySchema": [
                {"AttributeName": "is_active", "KeyType": "HASH"},
                {"AttributeName": "popularity_score", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["term", "category", "definition"]},
        },
        {
            "IndexName": "TrendingCategoryIndex",
            "KeySchema": [
                {"AttributeName": "category", "KeyType": "HASH"},
                {"AttributeName": "popularity_score", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["term", "definition", "is_active"]},
        },
    ]

    _create_table(
        moto_dynamodb,
        table_name=table_name,
        attribute_definitions=attribute_definitions,
        key_schema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        global_secondary_indexes=global_secondary_indexes,
    )

    aws_services._dynamodb_resource = moto_dynamodb  # type: ignore[attr-defined]
    aws_services._dynamodb_client = moto_dynamodb.meta.client  # type: ignore[attr-defined]
    return table_name


@pytest.fixture
def mock_config() -> Generator[Any, None, None]:
    """Mock configuration for testing."""
    from unittest.mock import Mock, patch
    from models.config import LLMConfig, UsageLimitsConfig, QuizConfig

    with patch('src.utils.config.ConfigService') as mock_config_class:
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.app_name = "lingible-backend"

        # Mock the get_config method to return actual Pydantic models
        def mock_get_config(config_type: Any, table_name: str | None = None) -> Any:
            if config_type == LLMConfig:
                return LLMConfig(
                    model="anthropic.claude-3-haiku-20240307-v1:0",
                    max_tokens=1000,
                    temperature=0.7,
                    top_p=0.9,
                    low_confidence_threshold=0.3,
                    lexicon_s3_bucket="test-bucket",
                    lexicon_s3_key="test-key",
                    age_max_rating="M18",
                    age_filter_mode="skip"
                )
            elif config_type == UsageLimitsConfig:
                return UsageLimitsConfig(
                    free_daily_translations=10,
                    premium_daily_translations=100,
                    free_max_text_length=100,
                    premium_max_text_length=500,
                    free_history_retention_days=7,
                    premium_history_retention_days=90
                )
            elif config_type == QuizConfig:
                return QuizConfig(
                    free_daily_limit=3,
                    premium_unlimited=False,
                    questions_per_quiz=10,
                    time_limit_seconds=60,
                    points_per_correct=10,
                    enable_time_bonus=True,
                )
            return Mock()

        # Mock _get_env_var for table names
        def mock_get_env_var(key: str) -> str:
            env_vars = {
                "USERS_TABLE": "test-users-table",
                "TRANSLATIONS_TABLE": "test-translations-table",
                "TERMS_TABLE": "test-terms-table",
                "LOG_LEVEL": "INFO",
                "ENABLE_TRACING": "false",
                "FREE_DAILY_TRANSLATIONS": "10",
                "PREMIUM_DAILY_TRANSLATIONS": "100",
                "FREE_MAX_TEXT_LENGTH": "100",
                "PREMIUM_MAX_TEXT_LENGTH": "500",
                "FREE_HISTORY_RETENTION_DAYS": "7",
                "PREMIUM_HISTORY_RETENTION_DAYS": "90",
            }
            return env_vars.get(key, "")

        mock_config.get_config.side_effect = mock_get_config
        mock_config._get_env_var = Mock(side_effect=mock_get_env_var)
        mock_config_class.return_value = mock_config
        yield mock_config


@pytest.fixture
def minimal_api_gateway_event() -> dict[str, Any]:
    """Create a minimal valid API Gateway event for unauthenticated handlers."""
    return {
        "resource": "/health",
        "path": "/health",
        "httpMethod": "GET",
        "headers": {},
        "multiValueHeaders": {},
        "requestContext": {
            "requestId": "test-request-id",
            "stage": "test",
            "apiId": "test-api-id",
            "resourceId": "test-resource-id",
            "resourcePath": "/health",
            "httpMethod": "GET",
            "requestTime": "09/Apr/2024:12:34:56 +0000",
            "requestTimeEpoch": 1712660096000,
            "identity": {
                "sourceIp": "127.0.0.1",
                "userAgent": "test-agent",
            },
            "accountId": "123456789012",
            "protocol": "HTTP/1.1",
            "path": "/test/health",
        },
    }


@pytest.fixture
def authenticated_api_gateway_event(minimal_api_gateway_event: dict[str, Any]) -> dict[str, Any]:
    """Create a minimal valid API Gateway event with authentication."""
    event = minimal_api_gateway_event.copy()
    event["requestContext"]["authorizer"] = {
        "claims": {
            "sub": "test-user-id",
            "email": "test@example.com",
            "aud": "test-client-id",
            "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
            "exp": 1234567890,
            "iat": 1234567890,
            "jti": "test-jti",
        }
    }
    return event


@pytest.fixture
def api_gateway_event_with_path_params(authenticated_api_gateway_event: dict[str, Any]) -> dict[str, Any]:
    """Create an authenticated API Gateway event with path parameters."""
    event = authenticated_api_gateway_event.copy()
    event["pathParameters"] = {}
    return event


@pytest.fixture
def api_gateway_event_with_query_params(authenticated_api_gateway_event: dict[str, Any]) -> dict[str, Any]:
    """Create an authenticated API Gateway event with query parameters."""
    event = authenticated_api_gateway_event.copy()
    event["queryStringParameters"] = {}
    event["multiValueQueryStringParameters"] = {}
    return event


@pytest.fixture
def api_gateway_event_with_body(authenticated_api_gateway_event: dict[str, Any]) -> dict[str, Any]:
    """Create an authenticated API Gateway event with request body."""
    event = authenticated_api_gateway_event.copy()
    event["body"] = "{}"
    event["headers"]["Content-Type"] = "application/json"
    event["multiValueHeaders"]["Content-Type"] = ["application/json"]
    return event
