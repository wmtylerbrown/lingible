"""Tests for repository layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from models.users import User, UserTier, UserStatus
from models.translations import Translation, TranslationDirection
from models.subscriptions import UserSubscription, SubscriptionStatus, SubscriptionProvider
from models.trending import TrendingTerm, TrendingCategory
from repositories.user_repository import UserRepository
from repositories.translation_repository import TranslationRepository
from repositories.subscription_repository import SubscriptionRepository
from repositories.trending_repository import TrendingRepository
from utils.exceptions import BusinessLogicError


class TestUserRepository:
    """Test UserRepository."""

    @pytest.fixture
    def user_repository(self, mock_dynamodb_table, mock_config):
        """Create UserRepository with mocked dependencies."""
        with patch('src.repositories.user_repository.aws_services') as mock_aws_services:
            mock_table = Mock()
            mock_aws_services.dynamodb_resource.Table.return_value = mock_table
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
                'tier': sample_user.tier,
                'status': sample_user.status,
                'created_at': sample_user.created_at.isoformat(),
                'updated_at': sample_user.updated_at.isoformat()
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

    def test_increment_usage_first_time_creates_record(self, user_repository):
        """Test that first usage increment creates a new record with proper reset_daily_at."""
        user_id = "test_user_123"

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            from datetime import datetime, timezone, timedelta
            now_utc = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)

            mock_datetime.now.return_value = now_utc
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Mock successful update (first try succeeds because reset_daily_at doesn't exist)
            user_repository.table.update_item.return_value = {"Attributes": {"daily_used": 1}}

            result = user_repository.increment_usage(user_id, UserTier.FREE)

            assert result is True

            # Verify the update call
            call_args = user_repository.table.update_item.call_args
            assert call_args[1]["Key"] == {"PK": f"USER#{user_id}", "SK": "USAGE#LIMITS"}

            # Check UpdateExpression includes both daily_used increment and reset_daily_at
            update_expr = call_args[1]["UpdateExpression"]
            assert "daily_used = if_not_exists(daily_used, 0) + :one" in update_expr
            assert "reset_daily_at = if_not_exists(reset_daily_at, :tomorrow_start)" in update_expr

            # Check attribute values
            attr_values = call_args[1]["ExpressionAttributeValues"]
            assert attr_values[":one"] == 1
            assert attr_values[":today_start"] == today_start.isoformat()
            assert attr_values[":tomorrow_start"] == tomorrow_start.isoformat()

            # Check condition allows creation
            condition = call_args[1]["ConditionExpression"]
            assert "attribute_not_exists(reset_daily_at) OR reset_daily_at > :today_start" in condition

    def test_increment_usage_same_day_increments(self, user_repository):
        """Test that usage increment on same day increments the counter."""
        user_id = "test_user_123"

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            from datetime import datetime, timezone
            now_utc = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = now_utc
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Mock successful update (condition passes because reset_daily_at > today_start)
            user_repository.table.update_item.return_value = {"Attributes": {"daily_used": 5}}

            result = user_repository.increment_usage(user_id, UserTier.FREE)

            assert result is True
            user_repository.table.update_item.assert_called_once()

    def test_increment_usage_new_day_resets_to_one(self, user_repository):
        """Test that usage increment on new day resets counter to 1."""
        user_id = "test_user_123"

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            from datetime import datetime, timezone, timedelta
            now_utc = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)

            mock_datetime.now.return_value = now_utc
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # First update fails (condition fails - it's a new day), second succeeds (reset logic)
            user_repository.table.update_item.side_effect = [
                ClientError({'Error': {'Code': 'ConditionalCheckFailedException'}}, 'UpdateItem'),
                {"Attributes": {"daily_used": 1}}
            ]

            result = user_repository.increment_usage(user_id, UserTier.FREE)

            assert result is True
            assert user_repository.table.update_item.call_count == 2

            # Check the fallback call (second call)
            fallback_call = user_repository.table.update_item.call_args_list[1]
            update_expr = fallback_call[1]["UpdateExpression"]
            assert "daily_used = :one" in update_expr
            assert "reset_daily_at = :tomorrow_start" in update_expr

            attr_values = fallback_call[1]["ExpressionAttributeValues"]
            assert attr_values[":one"] == 1
            assert attr_values[":tomorrow_start"] == tomorrow_start.isoformat()

    def test_reset_daily_usage_sets_tomorrow(self, user_repository):
        """Test that reset_daily_usage sets reset_daily_at to tomorrow."""
        user_id = "test_user_123"

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            from datetime import datetime, timezone, timedelta
            now_utc = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)

            mock_datetime.now.return_value = now_utc
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            user_repository.table.update_item.return_value = {}

            result = user_repository.reset_daily_usage(user_id, UserTier.FREE)

            assert result is True

            call_args = user_repository.table.update_item.call_args
            update_expr = call_args[1]["UpdateExpression"]
            assert "daily_used = :zero" in update_expr
            assert "reset_daily_at = :tomorrow_start" in update_expr

            attr_values = call_args[1]["ExpressionAttributeValues"]
            assert attr_values[":zero"] == 0
            assert attr_values[":tomorrow_start"] == tomorrow_start.isoformat()

    def test_increment_usage_validates_dynamodb_expressions(self, user_repository):
        """Test that increment_usage generates correct DynamoDB update expressions."""
        user_id = "test_user_123"

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            from datetime import datetime, timezone, timedelta
            now_utc = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)

            mock_datetime.now.return_value = now_utc
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Mock successful update_item
            user_repository.table.update_item.return_value = {"Attributes": {"daily_used": 1}}

            # Call increment_usage
            result = user_repository.increment_usage(user_id, UserTier.FREE)
            assert result is True

            # Verify the exact update_item call
            user_repository.table.update_item.assert_called_once()
            call_kwargs = user_repository.table.update_item.call_args[1]

            # Validate Key
            assert call_kwargs["Key"] == {"PK": f"USER#{user_id}", "SK": "USAGE#LIMITS"}

            # Validate UpdateExpression - this is the critical part!
            update_expr = call_kwargs["UpdateExpression"]
            print(f"UpdateExpression: {update_expr}")

            # Must contain the increment operation
            assert "daily_used = if_not_exists(daily_used, :zero) + :one" in update_expr
            # Must set reset_daily_at when it doesn't exist
            assert "reset_daily_at = if_not_exists(reset_daily_at, :tomorrow_start)" in update_expr
            # Must update timestamp
            assert "updated_at = :updated_at" in update_expr
            # Must set tier if it doesn't exist
            assert "tier = if_not_exists(tier, :tier)" in update_expr

            # Validate ExpressionAttributeValues - critical for increment!
            attr_values = call_kwargs["ExpressionAttributeValues"]
            print(f"ExpressionAttributeValues: {attr_values}")

            assert attr_values[":zero"] == 0  # Default value for if_not_exists
            assert attr_values[":one"] == 1  # This is what gets added!
            assert attr_values[":today_start"] == today_start.isoformat()
            assert attr_values[":tomorrow_start"] == tomorrow_start.isoformat()
            assert attr_values[":updated_at"] == now_utc.isoformat()
            assert attr_values[":tier"] == "free"

            # Validate ConditionExpression
            condition = call_kwargs["ConditionExpression"]
            print(f"ConditionExpression: {condition}")
            assert "attribute_not_exists(reset_daily_at) OR reset_daily_at > :today_start" in condition

            # Validate return values
            assert call_kwargs["ReturnValues"] == "UPDATED_NEW"

    def test_increment_usage_actual_increment_behavior(self, user_repository):
        """Test that increment_usage actually increments values correctly."""
        user_id = "test_user_123"

        # Create a mock that tracks what values are being passed
        call_history = []

        def track_update_calls(**kwargs):
            call_history.append(kwargs)
            # Simulate successful update with incremented value
            update_expr = kwargs.get('UpdateExpression', '')
            attr_values = kwargs.get('ExpressionAttributeValues', {})

            if 'daily_used = if_not_exists(daily_used, 0) + :one' in update_expr:
                increment_value = attr_values.get(':one', 0)
                # Simulate the result of the increment
                new_value = len(call_history)  # Simulates incrementing from 0, 1, 2, etc.
                return {"Attributes": {"daily_used": new_value}}

            return {"Attributes": {"daily_used": 1}}

        user_repository.table.update_item.side_effect = track_update_calls

        # Call increment_usage multiple times
        for i in range(3):
            result = user_repository.increment_usage(user_id, UserTier.FREE)
            assert result is True, f"Increment {i+1} should succeed"

        # Verify we made 3 calls
        assert len(call_history) == 3

        # Verify each call tried to increment by 1
        for i, call in enumerate(call_history):
            attr_values = call["ExpressionAttributeValues"]
            assert attr_values[":one"] == 1, f"Call {i+1} should increment by 1"

            update_expr = call["UpdateExpression"]
            assert "daily_used = if_not_exists(daily_used, 0) + :one" in update_expr, f"Call {i+1} should use increment expression"

    def test_increment_usage_with_old_reset_daily_at_bug(self, user_repository):
        """Test increment behavior when reset_daily_at is incorrectly set to today (old bug)."""
        user_id = "test_user_123"

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            from datetime import datetime, timezone, timedelta
            # Current time: afternoon of Dec 19
            now_utc = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_start = today_start + timedelta(days=1)

            mock_datetime.now.return_value = now_utc
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Simulate the bug: first call fails because condition fails
            # This happens when reset_daily_at was previously set to today_start (not tomorrow_start)
            from botocore.exceptions import ClientError

            user_repository.table.update_item.side_effect = [
                # First call fails due to condition (reset_daily_at = today_start, not > today_start)
                ClientError({'Error': {'Code': 'ConditionalCheckFailedException'}}, 'UpdateItem'),
                # Second call succeeds (fallback reset logic)
                {"Attributes": {"daily_used": 1}}
            ]

            result = user_repository.increment_usage(user_id, UserTier.FREE)
            assert result is True

            # Verify it made 2 calls (first failed, second succeeded)
            assert user_repository.table.update_item.call_count == 2

            # Check the first call (the one that failed)
            first_call = user_repository.table.update_item.call_args_list[0]
            first_kwargs = first_call[1]

            # This call has the increment expression
            assert "daily_used = if_not_exists(daily_used, 0) + :one" in first_kwargs["UpdateExpression"]

            # The condition that fails when reset_daily_at is set to today_start
            condition = first_kwargs["ConditionExpression"]
            assert "reset_daily_at > :today_start" in condition

            # Check the second call (fallback reset)
            second_call = user_repository.table.update_item.call_args_list[1]
            second_kwargs = second_call[1]

            # This call resets to 1
            assert "daily_used = :one" in second_kwargs["UpdateExpression"]
            assert second_kwargs["ExpressionAttributeValues"][":one"] == 1

            print(f"✅ Test confirms the bug: When reset_daily_at is set to today_start,")
            print(f"   the condition fails and daily_used gets reset to 1 instead of incrementing.")

    def test_increment_usage_with_real_dynamodb_table(self):
        """CRITICAL TEST: Use real moto DynamoDB to test increment operations."""
        from moto import mock_aws
        import boto3
        from src.repositories.user_repository import UserRepository
        from src.models.users import UserTier

        with mock_aws():
            # Create a real DynamoDB table using moto
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

            table_name = 'test-users-table'
            table = dynamodb.create_table(
                TableName=table_name,
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

            # Wait for table to be ready
            table.wait_until_exists()

            # Create repository and directly assign the table
            with patch('src.repositories.user_repository.aws_services') as mock_aws_services:
                with patch('src.repositories.user_repository.get_config_service') as mock_get_config:
                    # Mock AWS services
                    mock_aws_services.dynamodb_resource = dynamodb

                    # Mock config to return our test table name
                    mock_config = Mock()
                    mock_config.get_config.return_value = Mock(name=table_name)
                    mock_get_config.return_value = mock_config

                    repo = UserRepository()
                    # Directly assign our moto table to ensure it's used
                    repo.table = table
                    user_id = "test_user_real_table"

                    print(f"\n🧪 Testing with REAL DynamoDB table (moto)")

                    # Test 1: First increment (creates record)
                    result1 = repo.increment_usage(user_id, UserTier.FREE)
                    assert result1 is True, "First increment should succeed"

                    # Verify the record was created correctly
                    usage_limits = repo.get_usage_limits(user_id)
                    assert usage_limits is not None, "Usage limits should exist"
                    assert usage_limits.daily_used == 1, f"Expected daily_used=1, got {usage_limits.daily_used}"

                    print(f"   ✅ First increment: daily_used = {usage_limits.daily_used}")

                    # Test 2: Second increment (should increment to 2)
                    result2 = repo.increment_usage(user_id, UserTier.FREE)
                    assert result2 is True, "Second increment should succeed"

                    usage_limits = repo.get_usage_limits(user_id)
                    assert usage_limits.daily_used == 2, f"Expected daily_used=2, got {usage_limits.daily_used}"

                    print(f"   ✅ Second increment: daily_used = {usage_limits.daily_used}")

                    # Test 3: Multiple increments to verify it keeps working
                    for i in range(3, 8):  # Increment to 7 total
                        result = repo.increment_usage(user_id, UserTier.FREE)
                        assert result is True, f"Increment {i} should succeed"

                        usage_limits = repo.get_usage_limits(user_id)
                        expected = i
                        actual = usage_limits.daily_used
                        assert actual == expected, f"Expected daily_used={expected}, got {actual}"

                        print(f"   ✅ Increment {i}: daily_used = {actual}")

                    # Test 4: Verify reset_daily_at is set correctly
                    from datetime import datetime, timezone, timedelta
                    usage_limits = repo.get_usage_limits(user_id)

                    now = datetime.now(timezone.utc)
                    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    tomorrow_start = today_start + timedelta(days=1)

                    reset_time = usage_limits.reset_daily_at
                    assert reset_time >= tomorrow_start, f"reset_daily_at should be tomorrow or later, got {reset_time}"

                    print(f"   ✅ reset_daily_at correctly set to: {reset_time}")

                    # Test 5: Manual reset works
                    reset_result = repo.reset_daily_usage(user_id, UserTier.FREE)
                    assert reset_result is True, "Reset should succeed"

                    usage_limits = repo.get_usage_limits(user_id)
                    assert usage_limits.daily_used == 0, f"After reset, expected daily_used=0, got {usage_limits.daily_used}"

                    print(f"   ✅ Manual reset: daily_used = {usage_limits.daily_used}")

                    # Test 6: Increment after reset works
                    result_after_reset = repo.increment_usage(user_id, UserTier.FREE)
                    assert result_after_reset is True, "Increment after reset should succeed"

                    usage_limits = repo.get_usage_limits(user_id)
                    assert usage_limits.daily_used == 1, f"After reset+increment, expected daily_used=1, got {usage_limits.daily_used}"

                    print(f"   ✅ Increment after reset: daily_used = {usage_limits.daily_used}")

                    print(f"\n🎉 ALL REAL DYNAMODB TESTS PASSED!")
                    print(f"   - DynamoDB expressions are syntactically correct")
                    print(f"   - Increment operations work with real data types")
                    print(f"   - Condition logic works correctly")
                    print(f"   - Reset functionality works")
                    print(f"   - No silent failures or type mismatches")

    def test_get_daily_quiz_count_not_found(self, user_repository):
        """Test get_daily_quiz_count returns 0 when item doesn't exist."""
        user_repository.table.get_item.return_value = {}

        result = user_repository.get_daily_quiz_count("user_123", "2024-12-19")

        assert result == 0

    def test_get_daily_quiz_count_exists(self, user_repository):
        """Test get_daily_quiz_count returns correct count when item exists."""
        user_repository.table.get_item.return_value = {
            "Item": {
                "PK": "USER#user_123",
                "SK": "QUIZ_DAILY#2024-12-19",
                "quiz_count": 3
            }
        }

        result = user_repository.get_daily_quiz_count("user_123", "2024-12-19")

        assert result == 3
        user_repository.table.get_item.assert_called_once_with(
            Key={
                "PK": "USER#user_123",
                "SK": "QUIZ_DAILY#2024-12-19",
            }
        )

    def test_get_daily_quiz_count_handles_error(self, user_repository):
        """Test get_daily_quiz_count handles errors gracefully."""
        user_repository.table.get_item.side_effect = Exception("Database error")

        result = user_repository.get_daily_quiz_count("user_123", "2024-12-19")

        assert result == 0

    def test_increment_daily_quiz_count_creates_with_ttl(self, user_repository):
        """Test increment_daily_quiz_count creates item with TTL if it doesn't exist."""
        from datetime import datetime, timezone, timedelta
        from unittest.mock import patch

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            today = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_date = today.date()
            date_obj = datetime.strptime(today_date.isoformat(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            expected_ttl = int((date_obj + timedelta(hours=48)).timestamp())

            mock_datetime.now.return_value = today
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            user_repository.table.update_item.return_value = {
                "Attributes": {
                    "quiz_count": 1,
                    "last_quiz_at": today.isoformat(),
                    "ttl": expected_ttl
                }
            }

            result = user_repository.increment_daily_quiz_count("user_123")

            assert result == 1
            call_args = user_repository.table.update_item.call_args
            assert call_args[1]["Key"] == {
                "PK": "USER#user_123",
                "SK": f"QUIZ_DAILY#{today_date.isoformat()}",
            }
            # Verify TTL is set
            expr_values = call_args[1]["ExpressionAttributeValues"]
            assert expr_values[":ttl"] == expected_ttl
            assert expr_values[":inc"] == 1

    def test_increment_daily_quiz_count_increments_existing(self, user_repository):
        """Test increment_daily_quiz_count increments existing count."""
        from datetime import datetime, timezone, timedelta
        from unittest.mock import patch

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            today = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_date = today.date()

            mock_datetime.now.return_value = today
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            user_repository.table.update_item.return_value = {
                "Attributes": {
                    "quiz_count": 4
                }
            }

            result = user_repository.increment_daily_quiz_count("user_123")

            assert result == 4

    def test_increment_daily_quiz_count_handles_error(self, user_repository):
        """Test increment_daily_quiz_count handles errors gracefully."""
        from datetime import datetime, timezone
        from unittest.mock import patch

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            today = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = today
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            user_repository.table.update_item.side_effect = Exception("Database error")

            result = user_repository.increment_daily_quiz_count("user_123")

            assert result == 1  # Returns 1 on error

    def test_delete_user_includes_quiz_cleanup(self, user_repository):
        """Test delete_user deletes all quiz daily count items."""
        # Mock successful deletions
        user_repository.table.delete_item.return_value = {}
        # Mock query for quiz items
        user_repository.table.query.return_value = {
            "Items": [
                {"PK": "USER#user_123", "SK": "QUIZ_DAILY#2024-12-19"},
                {"PK": "USER#user_123", "SK": "QUIZ_DAILY#2024-12-18"},
            ]
        }

        result = user_repository.delete_user("user_123")

        assert result is True
        # Should delete profile, usage limits, and 2 quiz items = 4 total deletions
        assert user_repository.table.delete_item.call_count == 4
        # Verify quiz items were queried
        user_repository.table.query.assert_called_once_with(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": "USER#user_123",
                ":sk_prefix": "QUIZ_DAILY#",
            },
        )

    def test_delete_user_handles_quiz_cleanup_error(self, user_repository):
        """Test delete_user handles quiz cleanup errors gracefully."""
        user_repository.table.delete_item.return_value = {}
        user_repository.table.query.side_effect = Exception("Query error")

        result = user_repository.delete_user("user_123")

        # Should still succeed, just deleting profile and usage limits
        assert result is True
        assert user_repository.table.delete_item.call_count == 2  # Profile and usage only

    def test_delete_daily_quiz_count_success(self, user_repository):
        """Test delete_daily_quiz_count successfully deletes item."""
        from datetime import datetime, timezone
        from unittest.mock import patch

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            today = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            today_str = today.date().isoformat()
            mock_datetime.now.return_value = today
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            user_repository.table.delete_item.return_value = {}

            result = user_repository.delete_daily_quiz_count("user_123")

            assert result is True
            user_repository.table.delete_item.assert_called_once_with(
                Key={
                    "PK": "USER#user_123",
                    "SK": f"QUIZ_DAILY#{today_str}",
                }
            )

    def test_delete_daily_quiz_count_handles_error(self, user_repository):
        """Test delete_daily_quiz_count handles errors gracefully."""
        from datetime import datetime, timezone
        from unittest.mock import patch

        with patch('src.repositories.user_repository.datetime') as mock_datetime:
            today = datetime(2024, 12, 19, 14, 30, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = today
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            user_repository.table.delete_item.side_effect = Exception("Database error")

            result = user_repository.delete_daily_quiz_count("user_123")

            assert result is False


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
                'direction': sample_translation.direction,
                'model_used': sample_translation.model_used,
                'confidence_score': sample_translation.confidence_score,
                'created_at': sample_translation.created_at.isoformat()
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
                'provider': sample_subscription.provider,
                'status': sample_subscription.status,
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


class TestTrendingRepository:
    """Test TrendingRepository with moto integration tests."""

    @pytest.fixture
    def trending_repository(self, mock_dynamodb_table, mock_config):
        """Create TrendingRepository with mocked dependencies."""
        with patch('repositories.trending_repository.aws_services') as mock_aws_services:
            mock_aws_services.dynamodb_resource.Table.return_value = mock_dynamodb_table
            repo = TrendingRepository()
            repo.table = mock_dynamodb_table
            return repo

    def test_create_trending_term(self, trending_repository, sample_trending_term):
        """Test creating a new trending term."""
        result = trending_repository.create_trending_term(sample_trending_term)

        assert result is True

        # Verify the term was stored correctly
        stored_term = trending_repository.get_trending_term(sample_trending_term.term)
        assert stored_term is not None
        assert stored_term.term == sample_trending_term.term
        assert stored_term.definition == sample_trending_term.definition
        assert stored_term.category == sample_trending_term.category
        assert stored_term.popularity_score == sample_trending_term.popularity_score

    def test_get_trending_term(self, trending_repository, sample_trending_term):
        """Test getting a trending term by name."""
        # First create the term
        trending_repository.create_trending_term(sample_trending_term)

        # Then retrieve it
        result = trending_repository.get_trending_term(sample_trending_term.term)

        assert result is not None
        assert result.term == sample_trending_term.term
        assert result.definition == sample_trending_term.definition

    def test_get_trending_term_not_found(self, trending_repository):
        """Test getting a non-existent trending term."""
        result = trending_repository.get_trending_term("nonexistent")
        assert result is None

    def test_update_trending_term(self, trending_repository, sample_trending_term):
        """Test updating a trending term."""
        # Create the term first
        trending_repository.create_trending_term(sample_trending_term)

        # Update it
        updated_term = sample_trending_term.model_copy()
        updated_term.definition = "Updated definition"
        updated_term.popularity_score = 95.0

        result = trending_repository.update_trending_term(updated_term)
        assert result is True

        # Verify the update
        stored_term = trending_repository.get_trending_term(sample_trending_term.term)
        assert stored_term.definition == "Updated definition"
        assert stored_term.popularity_score == 95.0

    @pytest.mark.skip(reason="Requires GSI indexes - complex DynamoDB setup needed")
    def test_get_trending_terms_all_categories(self, trending_repository, sample_trending_term):
        """Test getting trending terms across all categories."""
        # Create multiple terms with different categories
        terms = [
            sample_trending_term,
            sample_trending_term.model_copy(update={"term": "bet", "category": "slang", "popularity_score": 78.0}),
            sample_trending_term.model_copy(update={"term": "main character", "category": "meme", "popularity_score": 65.0}),
        ]

        # Mock the scan operation to return multiple terms
        with patch.object(trending_repository.table, 'scan') as mock_scan:
            mock_scan.return_value = {
                'Items': [
                    {
                        'PK': f'TERM#{term.term.lower()}',
                        'SK': 'METADATA#trending',
                        'term': term.term,
                        'definition': term.definition,
                        'category': term.category,
                        'popularity_score': term.popularity_score,
                        'search_count': term.search_count,
                        'translation_count': term.translation_count,
                        'first_seen': term.first_seen.isoformat(),
                        'last_updated': term.last_updated.isoformat(),
                        'is_active': term.is_active,
                        'example_usage': term.example_usage,
                        'origin': term.origin,
                        'related_terms': term.related_terms,
                    }
                    for term in terms
                ]
            }

            # Get all trending terms
            result = trending_repository.get_trending_terms(limit=10)

            assert len(result) == 3
            # Should be sorted by popularity score descending
            assert result[0].popularity_score >= result[1].popularity_score
            assert result[1].popularity_score >= result[2].popularity_score

    @pytest.mark.skip(reason="Requires GSI indexes - complex DynamoDB setup needed")
    def test_get_trending_terms_by_category(self, trending_repository, sample_trending_term):
        """Test getting trending terms filtered by category."""
        # Create terms with different categories
        slang_term = sample_trending_term
        meme_term = sample_trending_term.model_copy(update={"term": "main character", "category": "meme"})

        # Mock the query operation to return only slang terms
        with patch.object(trending_repository.table, 'query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {
                        'PK': f'TERM#{slang_term.term.lower()}',
                        'SK': 'METADATA#trending',
                        'term': slang_term.term,
                        'definition': slang_term.definition,
                        'category': slang_term.category,
                        'popularity_score': slang_term.popularity_score,
                        'search_count': slang_term.search_count,
                        'translation_count': slang_term.translation_count,
                        'first_seen': slang_term.first_seen.isoformat(),
                        'last_updated': slang_term.last_updated.isoformat(),
                        'is_active': slang_term.is_active,
                        'example_usage': slang_term.example_usage,
                        'origin': slang_term.origin,
                        'related_terms': slang_term.related_terms,
                    }
                ]
            }

            # Get only slang terms (uses GSI8)
            result = trending_repository.get_trending_terms(category=TrendingCategory.SLANG)

            assert len(result) == 1
            assert result[0].category == TrendingCategory.SLANG
            assert result[0].term == "no cap"
            # Verify GSI8 was used for category query
            assert mock_query.called
            call_kwargs = mock_query.call_args[1] if mock_query.call_args else {}
            assert call_kwargs.get('IndexName') == 'GSI8'

    def test_get_trending_terms_active_only(self, trending_repository, sample_trending_term):
        """Test getting only active trending terms."""
        # Create active and inactive terms
        active_term = sample_trending_term
        inactive_term = sample_trending_term.model_copy(update={"term": "old term", "is_active": False})

        # Mock the query operation using GSI7 for active terms
        with patch.object(trending_repository.table, 'query') as mock_query:
            mock_query.return_value = {
                'Items': [
                    {
                        'PK': f'TERM#{active_term.term.lower()}',
                        'SK': 'METADATA#trending',
                        'term': active_term.term,
                        'definition': active_term.definition,
                        'category': active_term.category,
                        'popularity_score': active_term.popularity_score,
                        'search_count': active_term.search_count,
                        'translation_count': active_term.translation_count,
                        'first_seen': active_term.first_seen.isoformat(),
                        'last_updated': active_term.last_updated.isoformat(),
                        'is_active': str(active_term.is_active),
                        'example_usage': active_term.example_usage,
                        'origin': active_term.origin,
                        'related_terms': active_term.related_terms,
                        'GSI7PK': 'TRENDING#True',
                        'GSI7SK': active_term.popularity_score,
                    }
                ]
            }

            # Get only active terms (uses GSI7)
            result = trending_repository.get_trending_terms(active_only=True)

            assert len(result) == 1
            assert result[0].is_active is True
            assert result[0].term == "no cap"
            # Verify GSI7 was used (query should be called with GSI7 index)
            assert mock_query.called
            call_kwargs = mock_query.call_args[1] if mock_query.call_args else {}
            assert call_kwargs.get('IndexName') == 'GSI7'

    def test_increment_search_count(self, trending_repository, sample_trending_term):
        """Test incrementing search count for a trending term."""
        # Create the term
        trending_repository.create_trending_term(sample_trending_term)

        # Increment search count
        result = trending_repository.increment_search_count(sample_trending_term.term)
        assert result is True

        # Verify the increment
        updated_term = trending_repository.get_trending_term(sample_trending_term.term)
        assert updated_term.search_count == sample_trending_term.search_count + 1

    def test_increment_translation_count(self, trending_repository, sample_trending_term):
        """Test incrementing translation count for a trending term."""
        # Create the term
        trending_repository.create_trending_term(sample_trending_term)

        # Increment translation count
        result = trending_repository.increment_translation_count(sample_trending_term.term)
        assert result is True

        # Verify the increment
        updated_term = trending_repository.get_trending_term(sample_trending_term.term)
        assert updated_term.translation_count == sample_trending_term.translation_count + 1

    @pytest.mark.skip(reason="Requires GSI indexes - complex DynamoDB setup needed")
    def test_get_trending_stats(self, trending_repository, sample_trending_term):
        """Test getting trending statistics."""
        # Create multiple terms
        terms = [
            sample_trending_term,
            sample_trending_term.model_copy(update={"term": "bet", "category": "slang"}),
            sample_trending_term.model_copy(update={"term": "old term", "is_active": False}),
        ]

        # Mock the query operations for stats
        with patch.object(trending_repository.table, 'query') as mock_query:
            mock_query.return_value = {
                'Count': 2  # Two active terms
            }

            # Get stats
            stats = trending_repository.get_trending_stats()

            assert "total_active_terms" in stats
            assert "category_counts" in stats
            assert "last_updated" in stats
            assert stats["total_active_terms"] == 2  # Only active terms
            assert stats["category_counts"]["slang"] == 2  # Two slang terms
            assert stats["category_counts"]["meme"] == 0  # No meme terms

    def test_trending_term_to_api_response_free_tier(self, sample_trending_term):
        """Test trending term API response for free tier users."""
        response = sample_trending_term.to_api_response("free")

        assert response.term == sample_trending_term.term
        assert response.definition == sample_trending_term.definition
        assert response.category == sample_trending_term.category
        assert response.popularity_score == sample_trending_term.popularity_score
        assert response.search_count == 0  # Hidden for free users
        assert response.translation_count == 0  # Hidden for free users
        assert response.example_usage is None  # Hidden for free users
        assert response.origin is None  # Hidden for free users
        assert response.related_terms == []  # Hidden for free users

    def test_trending_term_to_api_response_premium_tier(self, sample_trending_term):
        """Test trending term API response for premium tier users."""
        response = sample_trending_term.to_api_response("premium")

        assert response.term == sample_trending_term.term
        assert response.definition == sample_trending_term.definition
        assert response.category == sample_trending_term.category
        assert response.popularity_score == sample_trending_term.popularity_score
        assert response.search_count == sample_trending_term.search_count  # Full data for premium
        assert response.translation_count == sample_trending_term.translation_count  # Full data for premium
        assert response.example_usage == sample_trending_term.example_usage  # Full data for premium
        assert response.origin == sample_trending_term.origin  # Full data for premium
        assert response.related_terms == sample_trending_term.related_terms  # Full data for premium
