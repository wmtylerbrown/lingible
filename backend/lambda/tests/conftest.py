"""Pytest configuration and fixtures for Lingible tests."""

import pytest
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import boto3
from moto import mock_aws

from models.users import User, UserTier, UserStatus
from models.translations import Translation, TranslationHistory, TranslationDirection, TranslationRequest
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
    original_log_level = os.environ.get('LOG_LEVEL')
    original_environment = os.environ.get('ENVIRONMENT')
    original_app_name = os.environ.get('APP_NAME')
    original_users_table = os.environ.get('USERS_TABLE')
    original_terms_table = os.environ.get('TERMS_TABLE')
    original_translations_table = os.environ.get('TRANSLATIONS_TABLE')

    original_quiz_free_limit = os.environ.get('QUIZ_FREE_DAILY_LIMIT')
    original_quiz_questions_per_quiz = os.environ.get('QUIZ_QUESTIONS_PER_QUIZ')
    original_quiz_time_limit = os.environ.get('QUIZ_TIME_LIMIT_SECONDS')
    original_quiz_points_per_correct = os.environ.get('QUIZ_POINTS_PER_CORRECT')
    original_quiz_enable_time_bonus = os.environ.get('QUIZ_ENABLE_TIME_BONUS')
    original_quiz_premium_unlimited = os.environ.get('QUIZ_PREMIUM_UNLIMITED')

    original_sensitive_patterns = os.environ.get('SENSITIVE_FIELD_PATTERNS')
    original_llm_model_id = os.environ.get('LLM_MODEL_ID')
    original_llm_max_tokens = os.environ.get('LLM_MAX_TOKENS')
    original_llm_temperature = os.environ.get('LLM_TEMPERATURE')
    original_llm_top_p = os.environ.get('LLM_TOP_P')
    original_llm_low_confidence = os.environ.get('LLM_LOW_CONFIDENCE_THRESHOLD')
    original_lexicon_bucket = os.environ.get('LEXICON_S3_BUCKET')
    original_lexicon_key = os.environ.get('LEXICON_S3_KEY')
    original_age_max_rating = os.environ.get('AGE_MAX_RATING')
    original_age_filter_mode = os.environ.get('AGE_FILTER_MODE')

    original_slang_auto_approval = os.environ.get('SLANG_VALIDATION_AUTO_APPROVAL_ENABLED')
    original_free_daily_translations = os.environ.get('FREE_DAILY_TRANSLATIONS')
    original_premium_daily_translations = os.environ.get('PREMIUM_DAILY_TRANSLATIONS')
    original_free_max_text_length = os.environ.get('FREE_MAX_TEXT_LENGTH')
    original_premium_max_text_length = os.environ.get('PREMIUM_MAX_TEXT_LENGTH')
    original_free_history_days = os.environ.get('FREE_HISTORY_RETENTION_DAYS')
    original_premium_history_days = os.environ.get('PREMIUM_HISTORY_RETENTION_DAYS')
    original_tavily_api_key = os.environ.get('TAVILY_API_KEY')
    original_slang_auto_threshold = os.environ.get('SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD')
    original_slang_web_search_enabled = os.environ.get('SLANG_VALIDATION_WEB_SEARCH_ENABLED')
    original_slang_max_search_results = os.environ.get('SLANG_VALIDATION_MAX_SEARCH_RESULTS')
    original_slang_submission_topic = os.environ.get('SLANG_SUBMISSIONS_TOPIC_ARN')
    original_slang_validation_topic = os.environ.get('SLANG_VALIDATION_REQUEST_TOPIC_ARN')

    # Set fake credentials and test environment
    os.environ['AWS_ACCESS_KEY_ID'] = 'fake_access_key'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'fake_secret_key'
    os.environ['AWS_SESSION_TOKEN'] = 'fake_session_token'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['LOG_LEVEL'] = 'INFO'
    os.environ['ENABLE_TRACING'] = 'false'
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['APP_NAME'] = 'lingible-backend-tests'
    os.environ['USERS_TABLE'] = 'test-users-table'
    os.environ['TERMS_TABLE'] = 'test-terms-table'
    os.environ['TRANSLATIONS_TABLE'] = 'test-translations-table'

    os.environ['QUIZ_FREE_DAILY_LIMIT'] = '3'
    os.environ['QUIZ_QUESTIONS_PER_QUIZ'] = '10'
    os.environ['QUIZ_TIME_LIMIT_SECONDS'] = '60'
    os.environ['QUIZ_POINTS_PER_CORRECT'] = '10'
    os.environ['QUIZ_ENABLE_TIME_BONUS'] = 'true'
    os.environ['QUIZ_PREMIUM_UNLIMITED'] = 'false'

    os.environ['SENSITIVE_FIELD_PATTERNS'] = '["authorization","cookie"]'
    os.environ['LLM_MODEL_ID'] = 'anthropic.claude-3-haiku-20240307-v1:0'
    os.environ['LLM_MAX_TOKENS'] = '4000'
    os.environ['LLM_TEMPERATURE'] = '0.7'
    os.environ['LLM_TOP_P'] = '0.9'
    os.environ['LLM_LOW_CONFIDENCE_THRESHOLD'] = '0.3'
    os.environ['LEXICON_S3_BUCKET'] = 'test-lexicon-bucket'
    os.environ['LEXICON_S3_KEY'] = 'lexicon.json'
    os.environ['AGE_MAX_RATING'] = 'M18'
    os.environ['AGE_FILTER_MODE'] = 'skip'

    os.environ['SLANG_VALIDATION_AUTO_APPROVAL_ENABLED'] = 'true'
    os.environ['SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD'] = '0.85'
    os.environ['SLANG_VALIDATION_WEB_SEARCH_ENABLED'] = 'false'
    os.environ['SLANG_VALIDATION_MAX_SEARCH_RESULTS'] = '3'
    os.environ['SLANG_SUBMISSIONS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:submissions'
    os.environ['SLANG_VALIDATION_REQUEST_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:validation'
    os.environ['FREE_DAILY_TRANSLATIONS'] = '5'
    os.environ['PREMIUM_DAILY_TRANSLATIONS'] = '50'
    os.environ['FREE_MAX_TEXT_LENGTH'] = '280'
    os.environ['PREMIUM_MAX_TEXT_LENGTH'] = '2000'
    os.environ['FREE_HISTORY_RETENTION_DAYS'] = '7'
    os.environ['PREMIUM_HISTORY_RETENTION_DAYS'] = '365'
    os.environ['TAVILY_API_KEY'] = 'fake-tavily-key'

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

    if original_log_level is not None:
        os.environ['LOG_LEVEL'] = original_log_level
    else:
        os.environ.pop('LOG_LEVEL', None)

    if original_environment is not None:
        os.environ['ENVIRONMENT'] = original_environment
    else:
        os.environ.pop('ENVIRONMENT', None)

    if original_app_name is not None:
        os.environ['APP_NAME'] = original_app_name
    else:
        os.environ.pop('APP_NAME', None)

    if original_users_table is not None:
        os.environ['USERS_TABLE'] = original_users_table
    else:
        os.environ.pop('USERS_TABLE', None)

    if original_terms_table is not None:
        os.environ['TERMS_TABLE'] = original_terms_table
    else:
        os.environ.pop('TERMS_TABLE', None)

    if original_translations_table is not None:
        os.environ['TRANSLATIONS_TABLE'] = original_translations_table
    else:
        os.environ.pop('TRANSLATIONS_TABLE', None)

    if original_quiz_free_limit is not None:
        os.environ['QUIZ_FREE_DAILY_LIMIT'] = original_quiz_free_limit
    else:
        os.environ.pop('QUIZ_FREE_DAILY_LIMIT', None)

    if original_quiz_questions_per_quiz is not None:
        os.environ['QUIZ_QUESTIONS_PER_QUIZ'] = original_quiz_questions_per_quiz
    else:
        os.environ.pop('QUIZ_QUESTIONS_PER_QUIZ', None)

    if original_quiz_time_limit is not None:
        os.environ['QUIZ_TIME_LIMIT_SECONDS'] = original_quiz_time_limit
    else:
        os.environ.pop('QUIZ_TIME_LIMIT_SECONDS', None)

    if original_quiz_points_per_correct is not None:
        os.environ['QUIZ_POINTS_PER_CORRECT'] = original_quiz_points_per_correct
    else:
        os.environ.pop('QUIZ_POINTS_PER_CORRECT', None)

    if original_quiz_enable_time_bonus is not None:
        os.environ['QUIZ_ENABLE_TIME_BONUS'] = original_quiz_enable_time_bonus
    else:
        os.environ.pop('QUIZ_ENABLE_TIME_BONUS', None)

    if original_quiz_premium_unlimited is not None:
        os.environ['QUIZ_PREMIUM_UNLIMITED'] = original_quiz_premium_unlimited
    else:
        os.environ.pop('QUIZ_PREMIUM_UNLIMITED', None)

    if original_sensitive_patterns is not None:
        os.environ['SENSITIVE_FIELD_PATTERNS'] = original_sensitive_patterns
    else:
        os.environ.pop('SENSITIVE_FIELD_PATTERNS', None)

    if original_llm_model_id is not None:
        os.environ['LLM_MODEL_ID'] = original_llm_model_id
    else:
        os.environ.pop('LLM_MODEL_ID', None)

    if original_llm_max_tokens is not None:
        os.environ['LLM_MAX_TOKENS'] = original_llm_max_tokens
    else:
        os.environ.pop('LLM_MAX_TOKENS', None)

    if original_llm_temperature is not None:
        os.environ['LLM_TEMPERATURE'] = original_llm_temperature
    else:
        os.environ.pop('LLM_TEMPERATURE', None)

    if original_llm_top_p is not None:
        os.environ['LLM_TOP_P'] = original_llm_top_p
    else:
        os.environ.pop('LLM_TOP_P', None)

    if original_llm_low_confidence is not None:
        os.environ['LLM_LOW_CONFIDENCE_THRESHOLD'] = original_llm_low_confidence
    else:
        os.environ.pop('LLM_LOW_CONFIDENCE_THRESHOLD', None)

    if original_lexicon_bucket is not None:
        os.environ['LEXICON_S3_BUCKET'] = original_lexicon_bucket
    else:
        os.environ.pop('LEXICON_S3_BUCKET', None)

    if original_lexicon_key is not None:
        os.environ['LEXICON_S3_KEY'] = original_lexicon_key
    else:
        os.environ.pop('LEXICON_S3_KEY', None)

    if original_age_max_rating is not None:
        os.environ['AGE_MAX_RATING'] = original_age_max_rating
    else:
        os.environ.pop('AGE_MAX_RATING', None)

    if original_age_filter_mode is not None:
        os.environ['AGE_FILTER_MODE'] = original_age_filter_mode
    else:
        os.environ.pop('AGE_FILTER_MODE', None)

    if original_slang_auto_approval is not None:
        os.environ['SLANG_VALIDATION_AUTO_APPROVAL_ENABLED'] = original_slang_auto_approval
    else:
        os.environ.pop('SLANG_VALIDATION_AUTO_APPROVAL_ENABLED', None)

    if original_slang_auto_threshold is not None:
        os.environ['SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD'] = original_slang_auto_threshold
    else:
        os.environ.pop('SLANG_VALIDATION_AUTO_APPROVAL_THRESHOLD', None)

    if original_slang_web_search_enabled is not None:
        os.environ['SLANG_VALIDATION_WEB_SEARCH_ENABLED'] = original_slang_web_search_enabled
    else:
        os.environ.pop('SLANG_VALIDATION_WEB_SEARCH_ENABLED', None)

    if original_slang_max_search_results is not None:
        os.environ['SLANG_VALIDATION_MAX_SEARCH_RESULTS'] = original_slang_max_search_results
    else:
        os.environ.pop('SLANG_VALIDATION_MAX_SEARCH_RESULTS', None)

    if original_slang_submission_topic is not None:
        os.environ['SLANG_SUBMISSIONS_TOPIC_ARN'] = original_slang_submission_topic
    else:
        os.environ.pop('SLANG_SUBMISSIONS_TOPIC_ARN', None)

    if original_slang_validation_topic is not None:
        os.environ['SLANG_VALIDATION_REQUEST_TOPIC_ARN'] = original_slang_validation_topic
    else:
        os.environ.pop('SLANG_VALIDATION_REQUEST_TOPIC_ARN', None)

    if original_free_daily_translations is not None:
        os.environ['FREE_DAILY_TRANSLATIONS'] = original_free_daily_translations
    else:
        os.environ.pop('FREE_DAILY_TRANSLATIONS', None)

    if original_premium_daily_translations is not None:
        os.environ['PREMIUM_DAILY_TRANSLATIONS'] = original_premium_daily_translations
    else:
        os.environ.pop('PREMIUM_DAILY_TRANSLATIONS', None)

    if original_free_max_text_length is not None:
        os.environ['FREE_MAX_TEXT_LENGTH'] = original_free_max_text_length
    else:
        os.environ.pop('FREE_MAX_TEXT_LENGTH', None)

    if original_premium_max_text_length is not None:
        os.environ['PREMIUM_MAX_TEXT_LENGTH'] = original_premium_max_text_length
    else:
        os.environ.pop('PREMIUM_MAX_TEXT_LENGTH', None)

    if original_free_history_days is not None:
        os.environ['FREE_HISTORY_RETENTION_DAYS'] = original_free_history_days
    else:
        os.environ.pop('FREE_HISTORY_RETENTION_DAYS', None)

    if original_premium_history_days is not None:
        os.environ['PREMIUM_HISTORY_RETENTION_DAYS'] = original_premium_history_days
    else:
        os.environ.pop('PREMIUM_HISTORY_RETENTION_DAYS', None)

    if original_tavily_api_key is not None:
        os.environ['TAVILY_API_KEY'] = original_tavily_api_key
    else:
        os.environ.pop('TAVILY_API_KEY', None)


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
    return TranslationHistory(
        translation_id="trans_789",
        user_id="test_user_123",
        original_text="Hello world",
        translated_text="Hola mundo",
        direction=TranslationDirection.ENGLISH_TO_GENZ,
        model_used="anthropic.claude-3-sonnet-20240229-v1:0",
        confidence_score=0.95,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
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
    from models.config import LLMConfig, UsageLimitsConfig, QuizConfig
    from decimal import Decimal

    with patch('src.utils.config.ConfigService') as mock_config_class:
        mock_config = Mock()
        mock_config.environment = "test"
        mock_config.app_name = "lingible-backend"

        # Mock the get_config method to return actual Pydantic models
        def mock_get_config(config_type, table_name=None):
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
                    points_per_correct=10,
                    enable_time_bonus=True,
                    time_limit_seconds=60,
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
