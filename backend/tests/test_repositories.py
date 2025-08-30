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
            mock_boto3.return_value.Table.return_value = mock_dynamodb_table
            repo = UserRepository()
            return repo

    def test_create_user(self, user_repository, sample_user, mock_dynamodb_table):
        """Test creating a new user."""
        with patch.object(mock_dynamodb_table, 'put_item') as mock_put:
            mock_put.return_value = {}

            result = user_repository.create_user(sample_user)

            assert result is True
            mock_put.assert_called_once()

    def test_get_user(self, user_repository, sample_user, mock_dynamodb_table):
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

        with patch.object(mock_dynamodb_table, 'get_item') as mock_get:
            mock_get.return_value = mock_response

            result = user_repository.get_user(sample_user.user_id)

            assert result is not None
            assert result.user_id == sample_user.user_id
            assert result.email == sample_user.email

    def test_get_user_not_found(self, user_repository, mock_dynamodb_table):
        """Test getting a user that doesn't exist."""
        with patch.object(mock_dynamodb_table, 'get_item') as mock_get:
            mock_get.return_value = {}

            result = user_repository.get_user("nonexistent_user")

            assert result is None

    def test_update_user(self, user_repository, sample_user, mock_dynamodb_table):
        """Test updating a user."""
        with patch.object(mock_dynamodb_table, 'update_item') as mock_update:
            mock_update.return_value = {}

            result = user_repository.update_user(sample_user)

            assert result is True
            mock_update.assert_called_once()

    def test_delete_user(self, user_repository, mock_dynamodb_table):
        """Test deleting a user."""
        with patch.object(mock_dynamodb_table, 'delete_item') as mock_delete:
            mock_delete.return_value = {}

            result = user_repository.delete_user("test_user_123")

            assert result is True
            # Should delete both profile and usage records
            assert mock_delete.call_count == 2

    def test_get_usage_limits(self, user_repository, mock_dynamodb_table):
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

        with patch.object(mock_dynamodb_table, 'get_item') as mock_get:
            mock_get.return_value = mock_response

            result = user_repository.get_usage_limits("test_user_123")

            assert result['daily_used'] == 5
            assert result['daily_limit'] == 10
            assert result['tier'] == 'free'

    def test_increment_usage_same_day(self, user_repository, mock_dynamodb_table):
        """Test incrementing usage on the same day."""
        with patch.object(mock_dynamodb_table, 'update_item') as mock_update:
            mock_update.return_value = {}

            result = user_repository.increment_usage("test_user_123")

            assert result is True
            mock_update.assert_called_once()

    def test_increment_usage_new_day(self, user_repository, mock_dynamodb_table):
        """Test incrementing usage on a new day (resets counter)."""
        # First call fails (condition check), second call succeeds (reset)
        with patch.object(mock_dynamodb_table, 'update_item') as mock_update:
            mock_update.side_effect = [ClientError({'Error': {'Code': 'ConditionalCheckFailedException'}}, 'UpdateItem'), {}]

            result = user_repository.increment_usage("test_user_123")

            assert result is True
            assert mock_update.call_count == 2

    def test_reset_daily_usage(self, user_repository, mock_dynamodb_table):
        """Test resetting daily usage counter."""
        with patch.object(mock_dynamodb_table, 'update_item') as mock_update:
            mock_update.return_value = {}

            result = user_repository.reset_daily_usage("test_user_123")

            assert result is True
            mock_update.assert_called_once()


class TestTranslationRepository:
    """Test TranslationRepository."""

    @pytest.fixture
    def translation_repository(self, mock_dynamodb_table, mock_config):
        """Create TranslationRepository with mocked dependencies."""
        with patch('src.repositories.translation_repository.boto3.resource') as mock_boto3:
            mock_boto3.return_value.Table.return_value = mock_dynamodb_table
            repo = TranslationRepository()
            return repo

    def test_create_translation(self, translation_repository, sample_translation, mock_dynamodb_table):
        """Test creating a new translation."""
        with patch.object(mock_dynamodb_table, 'put_item') as mock_put:
            mock_put.return_value = {}

            result = translation_repository.create_translation(sample_translation)

            assert result is True
            mock_put.assert_called_once()

    def test_get_translation(self, translation_repository, sample_translation, mock_dynamodb_table):
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

        with patch.object(mock_dynamodb_table, 'get_item') as mock_get:
            mock_get.return_value = mock_response

            result = translation_repository.get_translation(
                sample_translation.user_id,
                sample_translation.translation_id
            )

            assert result is not None
            assert result.translation_id == sample_translation.translation_id
            assert result.original_text == sample_translation.original_text

    def test_get_user_translations(self, translation_repository, mock_dynamodb_table):
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
                    'translation_id': 'trans_2',
                    'user_id': 'test_user_123',
                    'original_text': 'World',
                    'translated_text': 'Mundo',
                    'direction': 'english_to_genz',
                    'created_at': '2024-01-01T00:00:00Z'
                }
            ]
        }

        with patch.object(mock_dynamodb_table, 'query') as mock_query:
            mock_query.return_value = mock_response

            result = translation_repository.get_user_translations("test_user_123", limit=10, offset=0)

            assert len(result) == 2
            assert result[0].translation_id == 'trans_1'
            assert result[1].translation_id == 'trans_2'

    def test_delete_translation(self, translation_repository, mock_dynamodb_table):
        """Test deleting a translation."""
        with patch.object(mock_dynamodb_table, 'delete_item') as mock_delete:
            mock_delete.return_value = {}

            result = translation_repository.delete_translation("test_user_123", "trans_789")

            assert result is True
            mock_delete.assert_called_once()

    def test_delete_user_translations(self, translation_repository, mock_dynamodb_table):
        """Test deleting all translations for a user."""
        mock_response = {
            'Items': [
                {'PK': 'USER#test_user_123', 'SK': 'TRANSLATION#trans_1'},
                {'PK': 'USER#test_user_123', 'SK': 'TRANSLATION#trans_2'}
            ]
        }

        with patch.object(mock_dynamodb_table, 'query') as mock_query, \
             patch.object(mock_dynamodb_table, 'delete_item') as mock_delete:
            mock_query.return_value = mock_response
            mock_delete.return_value = {}

            result = translation_repository.delete_user_translations("test_user_123")

            assert result is True
            # Should delete each translation
            assert mock_delete.call_count == 2


class TestSubscriptionRepository:
    """Test SubscriptionRepository."""

    @pytest.fixture
    def subscription_repository(self, mock_dynamodb_table, mock_config):
        """Create SubscriptionRepository with mocked dependencies."""
        with patch('src.repositories.subscription_repository.boto3.resource') as mock_boto3:
            mock_boto3.return_value.Table.return_value = mock_dynamodb_table
            repo = SubscriptionRepository()
            return repo

    def test_create_subscription(self, subscription_repository, sample_subscription, mock_dynamodb_table):
        """Test creating a new subscription."""
        with patch.object(mock_dynamodb_table, 'put_item') as mock_put:
            mock_put.return_value = {}

            result = subscription_repository.create_subscription(sample_subscription)

            assert result is True
            mock_put.assert_called_once()

    def test_get_active_subscription(self, subscription_repository, sample_subscription, mock_dynamodb_table):
        """Test getting active subscription for a user."""
        mock_response = {
            'Item': {
                'PK': f'USER#{sample_subscription.user_id}',
                'SK': f'SUBSCRIPTION#{sample_subscription.subscription_id}',
                'subscription_id': sample_subscription.subscription_id,
                'user_id': sample_subscription.user_id,
                'provider': sample_subscription.provider.value,
                'product_id': sample_subscription.product_id,
                'status': sample_subscription.status.value,
                'start_date': sample_subscription.start_date,
                'end_date': sample_subscription.end_date,
                'created_at': sample_subscription.created_at,
                'updated_at': sample_subscription.updated_at
            }
        }

        with patch.object(mock_dynamodb_table, 'get_item') as mock_get:
            mock_get.return_value = mock_response

            result = subscription_repository.get_active_subscription(sample_subscription.user_id)

            assert result is not None
            assert result.subscription_id == sample_subscription.subscription_id
            assert result.status == sample_subscription.status

    def test_get_active_subscription_not_found(self, subscription_repository, mock_dynamodb_table):
        """Test getting active subscription when none exists."""
        with patch.object(mock_dynamodb_table, 'get_item') as mock_get:
            mock_get.return_value = {}

            result = subscription_repository.get_active_subscription("test_user_123")

            assert result is None

    def test_cancel_subscription(self, subscription_repository, mock_dynamodb_table):
        """Test canceling a subscription."""
        with patch.object(mock_dynamodb_table, 'update_item') as mock_update:
            mock_update.return_value = {}

            result = subscription_repository.cancel_subscription("sub_123")

            assert result is True
            mock_update.assert_called_once()

    def test_get_subscription_by_transaction(self, subscription_repository, sample_subscription, mock_dynamodb_table):
        """Test getting subscription by transaction ID."""
        mock_response = {
            'Items': [{
                'PK': f'USER#{sample_subscription.user_id}',
                'SK': f'SUBSCRIPTION#{sample_subscription.subscription_id}',
                'subscription_id': sample_subscription.subscription_id,
                'transaction_id': 'txn_123'
            }]
        }

        with patch.object(mock_dynamodb_table, 'query') as mock_query:
            mock_query.return_value = mock_response

            result = subscription_repository.get_subscription_by_transaction("txn_123")

            assert result is not None
            assert result.subscription_id == sample_subscription.subscription_id
