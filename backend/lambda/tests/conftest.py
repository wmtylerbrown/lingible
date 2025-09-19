"""Pytest configuration and fixtures for Lingible tests."""

import pytest
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import boto3
from moto import mock_aws

from models.users import User, UserTier, UserStatus
from models.translations import Translation, TranslationDirection, TranslationRequest
from models.subscriptions import UserSubscription, SubscriptionStatus, SubscriptionProvider
from models.events import TranslationEvent, SimpleAuthenticatedEvent, PathParameterEvent
from models.trending import TrendingTerm, TrendingCategory, TrendingJobRequest


@pytest.fixture(autouse=True)
def fake_aws_credentials():
    """Set fake AWS credentials for all tests to prevent accidental real AWS usage."""
    # Store original values
    original_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    original_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    original_session_token = os.environ.get('AWS_SESSION_TOKEN')
    original_region = os.environ.get('AWS_DEFAULT_REGION')

    # Set fake credentials
    os.environ['AWS_ACCESS_KEY_ID'] = 'fake_access_key'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'fake_secret_key'
    os.environ['AWS_SESSION_TOKEN'] = 'fake_session_token'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

    yield

    # Restore original values
    if original_access_key is not None:
        os.environ['AWS_ACCESS_KEY_ID'] = original_access_key
    else:
        os.environ.pop('AWS_ACCESS_KEY_ID', None)

    if original_secret_key is not None:
        os.environ['AWS_SECRET_ACCESS_KEY'] = original_secret_key
    else:
        os.environ.pop('AWS_SECRET_ACCESS_KEY', None)

    if original_session_token is not None:
        os.environ['AWS_SESSION_TOKEN'] = original_session_token
    else:
        os.environ.pop('AWS_SESSION_TOKEN', None)

    if original_region is not None:
        os.environ['AWS_DEFAULT_REGION'] = original_region
    else:
        os.environ.pop('AWS_DEFAULT_REGION', None)


@pytest.fixture
def mock_aws_services():
    """Mock AWS services for testing."""
    with mock_aws(["dynamodb", "cognito-idp", "secretsmanager"]):
        yield


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        user_id="test_user_123",
        email="test@example.com",
        username="testuser",
        tier=UserTier.FREE,
        status=UserStatus.ACTIVE,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_premium_user():
    """Sample premium user for testing."""
    return User(
        user_id="premium_user_456",
        email="premium@example.com",
        username="premiumuser",
        tier=UserTier.PREMIUM,
        status=UserStatus.ACTIVE,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_translation():
    """Sample translation for testing."""
    return Translation(
        translation_id="trans_789",
        user_id="test_user_123",
        original_text="Hello world",
        translated_text="Hola mundo",
        direction=TranslationDirection.ENGLISH_TO_GENZ,
        model_used="anthropic.claude-3-sonnet-20240229-v1:0",
        confidence_score=0.95,
        created_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_subscription():
    """Sample subscription for testing."""
    return UserSubscription(
        user_id="premium_user_456",
        provider=SubscriptionProvider.APPLE,
        transaction_id="txn_123",
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_translation_request_event():
    """Sample translation request event for testing."""
    return TranslationEvent(
        event={},
        request_body=TranslationRequest(
            text="Hello world",
            direction=TranslationDirection.ENGLISH_TO_GENZ
        ),
        user_id="test_user_123",
        username="testuser",
        request_id="req_123",
        timestamp="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def mock_bedrock_client():
    """Mock AWS Bedrock client."""
    mock_client = Mock()
    mock_response = {
        "body": Mock()
    }
    mock_response["body"].read.return_value = '{"completion": "Hola mundo", "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 5}}'
    mock_client.invoke_model.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='lingible-users-dev',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table


@pytest.fixture
def mock_cognito_user_pool():
    """Mock Cognito User Pool."""
    with mock_aws(["cognito-idp"]):
        client = boto3.client('cognito-idp', region_name='us-east-1')
        response = client.create_user_pool(
            PoolName='lingible-users-dev',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False
                }
            }
        )
        yield response['UserPool']


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch('src.utils.logging.logger') as mock:
        yield mock


@pytest.fixture
def mock_tracer():
    """Mock tracer for testing."""
    with patch('src.utils.tracing.tracer') as mock:
        yield mock


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    from models.config import BedrockModel, TableConfigModel, LimitsModel, TranslationModel

    with patch('src.utils.config.ConfigService') as mock_config_class:
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.app_name = "lingible-backend"

        # Mock the get_config method to return actual Pydantic models
        def mock_get_config(config_type, table_name=None):
            if config_type == BedrockModel:
                return BedrockModel(
                    model="anthropic.claude-3-sonnet-20240229-v1:0",
                    region="us-east-1",
                    max_tokens=1000,
                    temperature=0.7
                )
            elif config_type == TableConfigModel:
                return TableConfigModel(name=f"lingible-{table_name}-test")
            elif config_type == LimitsModel:
                return LimitsModel(
                    free_daily_limit=10,
                    premium_daily_limit=1000,
                    max_text_length=1000
                )
            elif config_type == TranslationModel:
                return TranslationModel(
                    max_text_length=1000,
                    claude_model="anthropic.claude-3-sonnet-20240229-v1:0"
                )
            return Mock()

        mock_config.get_config.side_effect = mock_get_config

        # Keep legacy methods for backward compatibility
        mock_config.get_bedrock_config.return_value = {
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "max_tokens": 1000,
            "temperature": 0.7,
        }
        mock_config.get_apple_store_config.return_value = {
            "bundle_id": "com.lingible.lingible",
            "private_key": "test_private_key",
            "key_id": "test_key_id",
            "team_id": "test_team_id"
        }
        mock_config.get_google_play_config.return_value = {
            "package_name": "com.lingible.lingible",
            "service_account_key": "test_key.json",
            "api_timeout": 10
        }
        mock_config.get_database_config.return_value = {
            "tables": {
                "users": "lingible-users-test",
                "translations": "lingible-translations-test",
                "trending": "lingible-trending-test"
            }
        }
        mock_config_class.return_value = mock_config
        yield mock_config


@pytest.fixture
def sample_trending_term():
    """Sample trending term for testing."""
    return TrendingTerm(
        term="no cap",
        definition="No lie, for real, I'm telling the truth",
        category=TrendingCategory.SLANG,
        popularity_score=85.5,
        search_count=150,
        translation_count=45,
        first_seen=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        is_active=True,
        example_usage="That movie was fire, no cap!",
        origin="Hip hop culture",
        related_terms=["fr", "for real", "deadass"]
    )


@pytest.fixture
def sample_trending_job_request():
    """Sample trending job request for testing."""
    return TrendingJobRequest(
        job_type="gen_z_slang_analysis",
        source="bedrock_ai",
        parameters={
            "model": "anthropic.claude-3-haiku-20240307-v1:0",
            "max_terms": 20,
            "categories": ["slang", "meme", "expression"]
        }
    )
