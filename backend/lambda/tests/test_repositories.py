"""Tests for repository layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from src.models.users import User, UserTier, UserStatus
from src.models.translations import Translation, TranslationDirection
from src.models.subscriptions import UserSubscription, SubscriptionStatus, SubscriptionProvider
from src.repositories.user_repository import UserRepository
from src.repositories.translation_repository import TranslationRepository
from src.repositories.subscription_repository import SubscriptionRepository
from src.utils.exceptions import BusinessLogicError


class TestUserRepository:
    """Test UserRepository."""

    @pytest.fixture
    def user_repository(self, mock_dynamodb_table, mock_config):
        """Create UserRepository with mocked dependencies."""
        with patch('src.repositories.user_repository.boto3.resource') as mock_boto3:
            mock_table = Mock()
            mock_boto3.return_value.Table.return_value = mock_table
            repo = UserRepository()
            repo.table = mock_table
            return repo

    def test_create_user(self, user_repository, sample_user):
        """Test creating a new user."""
        user_repository.table.put_item.return_value = {}

        result = user_repository.create_user(sample_user)

        assert result is True
        user_repository.table.put_item.assert_called_once()

    def test_get_user(self, user_repository, sample_user):
        """Test getting a user by ID."""
        mock_response = {
            'Item': {
                'PK': f'USER#{sample_user.user_id}',
                'SK': 'PROFILE',
                'user_id': sample_user.user_id,
                'email': sample_user.email,
                'username': sample_user.username,
                'tier': sample_user.tier.value,
                'status': sample_user.status.value,
                'created_at': sample_user.created_at,
                'updated_at': sample_user.updated_at
            }
        }

        user_repository.table.get_item.return_value = mock_response

        result = user_repository.get_user(sample_user.user_id)

        assert result is not None
        assert result.user_id == sample_user.user_id
        assert result.email == sample_user.email

    def test_get_user_not_found(self, user_repository):
        """Test getting a user that doesn't exist."""
        user_repository.table.get_item.return_value = {}

        result = user_repository.get_user("nonexistent_user")

        assert result is None

    def test_update_user(self, user_repository, sample_user):
        """Test updating a user."""
        user_repository.table.update_item.return_value = {}

        result = user_repository.update_user(sample_user)

        assert result is True
        user_repository.table.update_item.assert_called_once()

    def test_delete_user(self, user_repository):
        """Test deleting a user."""
        user_repository.table.delete_item.return_value = {}

        result = user_repository.delete_user("test_user_123")

        assert result is True
        # Should delete both profile and usage records
        assert user_repository.table.delete_item.call_count == 2

    def test_get_usage_limits(self, user_repository):
        """Test getting user usage limits."""
        mock_response = {
            'Item': {
                'PK': 'USER#test_user_123',
                'SK': 'USAGE#LIMITS',
                'daily_used': 5,
                'daily_limit': 10,
                'tier': 'free',
                'reset_daily_at': '2024-01-01T00:00:00Z'
            }
        }

        user_repository.table.get_item.return_value = mock_response

        result = user_repository.get_usage_limits("test_user_123")

        assert result['daily_used'] == 5
        assert result['daily_limit'] == 10
        assert result['tier'] == 'free'

    def test_increment_usage_same_day(self, user_repository):
        """Test incrementing usage on the same day."""
        user_repository.table.update_item.return_value = {}

        result = user_repository.increment_usage("test_user_123")

        assert result is True
        user_repository.table.update_item.assert_called_once()

    def test_increment_usage_new_day(self, user_repository):
        """Test incrementing usage on a new day (resets counter)."""
        # First call fails (condition check), second call succeeds (reset)
        user_repository.table.update_item.side_effect = [
            ClientError({'Error': {'Code': 'ConditionalCheckFailedException'}}, 'UpdateItem'),
            {}
        ]

        result = user_repository.increment_usage("test_user_123")

        assert result is True
        assert user_repository.table.update_item.call_count == 2

    def test_reset_daily_usage(self, user_repository):
        """Test resetting daily usage counter."""
        user_repository.table.update_item.return_value = {}

        result = user_repository.reset_daily_usage("test_user_123")

        assert result is True
        user_repository.table.update_item.assert_called_once()


class TestTranslationRepository:
    """Test TranslationRepository."""

    @pytest.fixture
    def translation_repository(self, mock_dynamodb_table, mock_config):
        """Create TranslationRepository with mocked dependencies."""
        with patch('src.repositories.translation_repository.boto3.resource') as mock_boto3:
            mock_table = Mock()
            mock_boto3.return_value.Table.return_value = mock_table
            repo = TranslationRepository()
            repo.table = mock_table
            return repo

    def test_create_translation(self, translation_repository, sample_translation):
        """Test creating a new translation."""
        translation_repository.table.put_item.return_value = {}

        result = translation_repository.create_translation(sample_translation)

        assert result is True
        translation_repository.table.put_item.assert_called_once()

    def test_get_translation(self, translation_repository, sample_translation):
        """Test getting a translation by ID."""
        mock_response = {
            'Item': {
                'PK': f'USER#{sample_translation.user_id}',
                'SK': f'TRANSLATION#{sample_translation.translation_id}',
                'translation_id': sample_translation.translation_id,
                'user_id': sample_translation.user_id,
                'original_text': sample_translation.original_text,
                'translated_text': sample_translation.translated_text,
                'direction': sample_translation.direction.value,
                'model_used': sample_translation.model_used,
                'confidence_score': sample_translation.confidence_score,
                'created_at': sample_translation.created_at
            }
        }

        translation_repository.table.get_item.return_value = mock_response

        result = translation_repository.get_translation(
            sample_translation.user_id,
            sample_translation.translation_id
        )

        assert result is not None
        assert result.translation_id == sample_translation.translation_id
        assert result.original_text == sample_translation.original_text

    def test_get_user_translations(self, translation_repository):
        """Test getting all translations for a user."""
        mock_response = {
            'Items': [
                {
                    'PK': 'USER#test_user_123',
                    'SK': 'TRANSLATION#trans_1',
                    'translation_id': 'trans_1',
                    'user_id': 'test_user_123',
                    'original_text': 'Hello',
                    'translated_text': 'Hola',
                    'direction': 'english_to_genz',
                    'created_at': '2024-01-01T00:00:00Z'
                },
                {
                    'PK': 'USER#test_user_123',
                    'SK': 'TRANSLATION#trans_2',
                    'user_id': 'test_user_123',
                    'translation_id': 'trans_2',
                    'original_text': 'World',
                    'translated_text': 'Mundo',
                    'direction': 'english_to_genz',
                    'created_at': '2024-01-01T00:00:00Z'
                }
            ]
        }

        translation_repository.table.query.return_value = mock_response

        result = translation_repository.get_user_translations("test_user_123", limit=10, offset=0)

        assert len(result) == 2
        assert result[0].translation_id == 'trans_1'
        assert result[1].translation_id == 'trans_2'

    def test_delete_translation(self, translation_repository):
        """Test deleting a translation."""
        translation_repository.table.delete_item.return_value = {}

        result = translation_repository.delete_translation("test_user_123", "trans_789")

        assert result is True
        translation_repository.table.delete_item.assert_called_once()

    def test_delete_user_translations(self, translation_repository):
        """Test deleting all translations for a user."""
        mock_response = {
            'Items': [
                {'PK': 'USER#test_user_123', 'SK': 'TRANSLATION#trans_1'},
                {'PK': 'USER#test_user_123', 'SK': 'TRANSLATION#trans_2'}
            ]
        }

        translation_repository.table.query.return_value = mock_response
        translation_repository.table.delete_item.return_value = {}

        result = translation_repository.delete_user_translations("test_user_123")

        assert result is True
        # Should delete each translation
        assert translation_repository.table.delete_item.call_count == 2


class TestSubscriptionRepository:
    """Test SubscriptionRepository."""

    @pytest.fixture
    def subscription_repository(self, mock_dynamodb_table, mock_config):
        """Create SubscriptionRepository with mocked dependencies."""
        with patch('src.repositories.subscription_repository.boto3.resource') as mock_boto3:
            mock_table = Mock()
            mock_boto3.return_value.Table.return_value = mock_table
            repo = SubscriptionRepository()
            repo.table = mock_table
            return repo

    def test_create_subscription(self, subscription_repository, sample_subscription):
        """Test creating a new subscription."""
        subscription_repository.table.put_item.return_value = {}

        result = subscription_repository.create_subscription(sample_subscription)

        assert result is True
        subscription_repository.table.put_item.assert_called_once()

    def test_get_active_subscription(self, subscription_repository, sample_subscription):
        """Test getting active subscription for a user."""
        mock_response = {
            'Item': {
                'PK': f'USER#{sample_subscription.user_id}',
                'SK': f'SUBSCRIPTION#{sample_subscription.transaction_id}',
                'transaction_id': sample_subscription.transaction_id,
                'user_id': sample_subscription.user_id,
                'provider': sample_subscription.provider.value,
                'status': sample_subscription.status.value,
                'start_date': sample_subscription.start_date.isoformat(),
                'end_date': sample_subscription.end_date.isoformat(),
                'created_at': sample_subscription.created_at.isoformat(),
                'updated_at': sample_subscription.updated_at.isoformat()
            }
        }

        subscription_repository.table.get_item.return_value = mock_response

        result = subscription_repository.get_active_subscription(sample_subscription.user_id)

        assert result is not None
        assert result.transaction_id == sample_subscription.transaction_id
        assert result.status == sample_subscription.status

    def test_get_active_subscription_not_found(self, subscription_repository):
        """Test getting active subscription when none exists."""
        subscription_repository.table.get_item.return_value = {}

        result = subscription_repository.get_active_subscription("test_user_123")

        assert result is None

    def test_cancel_subscription(self, subscription_repository):
        """Test canceling a subscription."""
        subscription_repository.table.update_item.return_value = {}

        result = subscription_repository.cancel_subscription("sub_123")

        assert result is True
        subscription_repository.table.update_item.assert_called_once()

    def test_get_subscription_by_transaction(self, subscription_repository, sample_subscription):
        """Test getting subscription by transaction ID."""
        mock_response = {
            'Items': [{
                'PK': f'USER#{sample_subscription.user_id}',
                'SK': f'SUBSCRIPTION#{sample_subscription.transaction_id}',
                'transaction_id': 'txn_123'
            }]
        }

        subscription_repository.table.query.return_value = mock_response

        result = subscription_repository.get_subscription_by_transaction("txn_123")

        assert result is not None
        assert result.transaction_id == sample_subscription.transaction_id
