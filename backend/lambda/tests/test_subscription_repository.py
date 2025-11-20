from __future__ import annotations

from datetime import datetime, timedelta, timezone

from unittest.mock import Mock

import pytest

from models.subscriptions import (
    SubscriptionProvider,
    SubscriptionStatus,
    UserSubscription,
)
from repositories.subscription_repository import SubscriptionRepository


def _subscription(user_id: str = "user-sub", transaction_id: str = "txn-123") -> UserSubscription:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return UserSubscription(
        user_id=user_id,
        provider=SubscriptionProvider.APPLE,
        transaction_id=transaction_id,
        status=SubscriptionStatus.ACTIVE,
        start_date=now,
        end_date=now + timedelta(days=30),
        created_at=now,
        updated_at=now,
    )


def test_create_and_get_subscription(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    subscription = _subscription()

    assert repository.create_subscription(subscription) is True

    stored = repository.get_active_subscription(subscription.user_id)
    assert stored is not None
    assert stored.transaction_id == subscription.transaction_id
    assert stored.status is SubscriptionStatus.ACTIVE


def test_update_subscription_overwrites_status(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    repository.table = moto_dynamodb.Table(users_table)
    subscription = _subscription()
    repository.create_subscription(subscription)

    updated = subscription.model_copy(
        update={
            "status": SubscriptionStatus.EXPIRED,
            "end_date": subscription.end_date + timedelta(days=5),
            "updated_at": datetime(2025, 2, 1, tzinfo=timezone.utc),
        }
    )

    assert repository.update_subscription(updated) is True
    item = repository.table.get_item(
        Key={"PK": f"USER#{subscription.user_id}", "SK": "SUBSCRIPTION#ACTIVE"}
    )["Item"]
    assert item["status"] == SubscriptionStatus.EXPIRED
    assert item["end_date"] == updated.end_date.isoformat()


def test_cancel_subscription_archives_history(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    subscription = _subscription(transaction_id="txn-archive")
    repository.create_subscription(subscription)

    assert repository.cancel_subscription(subscription.user_id) is True
    assert repository.get_active_subscription(subscription.user_id) is None

    table = moto_dynamodb.Table(users_table)
    history_key = {
        "PK": f"USER#{subscription.user_id}",
        "SK": f"SUBSCRIPTION#HISTORY#{subscription.transaction_id}",
    }
    history_item = table.get_item(Key=history_key)["Item"]
    assert history_item["status"] == "cancelled"
    assert history_item["transaction_id"] == subscription.transaction_id


def test_cancel_subscription_without_active_returns_true(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    assert repository.cancel_subscription("no-sub") is True


def test_create_subscription_handles_exception(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    repository.table = Mock()
    repository.table.put_item.side_effect = RuntimeError("boom")
    assert repository.create_subscription(_subscription()) is False


def test_get_active_subscription_handles_exception(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    repository.table = Mock()
    repository.table.get_item.side_effect = RuntimeError("boom")
    assert repository.get_active_subscription("user-sub") is None


def test_update_subscription_handles_exception(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    repository.table = Mock()
    repository.table.put_item.side_effect = RuntimeError("boom")
    assert repository.update_subscription(_subscription()) is False


def test_cancel_subscription_handles_exception(users_table: str, moto_dynamodb) -> None:
    repository = SubscriptionRepository()
    repository.get_active_subscription = Mock(side_effect=RuntimeError("boom"))
    assert repository.cancel_subscription("user-sub") is False


def test_find_by_transaction_id_logs_and_returns_none(
    users_table: str, moto_dynamodb, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubscriptionRepository()
    spy_logger = Mock()
    spy_logger.log_error = Mock()
    spy_logger.log_business_event = Mock()
    monkeypatch.setattr("repositories.subscription_repository.logger", spy_logger)

    assert repository.find_by_transaction_id("txn-lookup") is None
    spy_logger.log_business_event.assert_called_once()


def test_find_by_transaction_id_handles_exception(
    users_table: str, moto_dynamodb, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = SubscriptionRepository()
    spy_logger = Mock()
    spy_logger.log_business_event.side_effect = RuntimeError("boom")
    spy_logger.log_error = Mock()
    monkeypatch.setattr("repositories.subscription_repository.logger", spy_logger)

    assert repository.find_by_transaction_id("txn-lookup") is None
    spy_logger.log_error.assert_called_once()
