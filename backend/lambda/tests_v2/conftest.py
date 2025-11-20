from __future__ import annotations

"""Shared fixtures for the v2 repository/service test suite."""

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
    os.environ.setdefault("APP_NAME", "lingible-backend-tests-v2")


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
        os.environ.setdefault("APP_NAME", "lingible-backend-tests-v2")

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
