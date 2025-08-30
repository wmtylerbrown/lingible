"""Pytest configuration and fixtures for Lingible tests."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import boto3
from moto import mock_aws

from src.models.users import User, UserTier, UserStatus
from src.models.translations import Translation, TranslationDirection, TranslationRequest
from src.models.subscriptions import UserSubscription, SubscriptionStatus, SubscriptionProvider
from src.models.events import TranslationEvent, SimpleAuthenticatedEvent, PathParameterEvent


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
    mock_response = Mock()
    mock_response["body"].read.return_value = '{"completion": "Hola mundo", "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 5}}'
    mock_client.invoke_model.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table."""
    with mock_aws(["dynamodb"]):
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
    with patch('src.utils.config.AppConfig') as mock_config_class:
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.app_name = "lingible-backend"
        mock_config.get_bedrock_config.return_value = {
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "max_tokens": 1000,
            "temperature": 0.7,
        }
        mock_config.get_apple_store_config.return_value = {
            "bundle_id": "com.lingible.lingible",
            "shared_secret": "test_secret",
            "sandbox_url": "https://sandbox.itunes.apple.com/verifyReceipt",
            "verify_url": "https://buy.itunes.apple.com/verifyReceipt"
        }
        mock_config.get_google_play_config.return_value = {
            "package_name": "com.lingible.lingible",
            "service_account_key": "test_key.json",
            "api_timeout": 10
        }
        mock_config.get_database_config.return_value = {
            "tables": {
                "users": "lingible-users-test",
                "translations": "lingible-translations-test"
            }
        }
        mock_config_class.return_value = mock_config
        yield mock_config
