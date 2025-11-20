from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from models.subscriptions import (
    ReceiptValidationRequest,
    ReceiptValidationResult,
    ReceiptValidationStatus,
    StoreEnvironment,
    SubscriptionProvider,
    SubscriptionStatus,
    TransactionData,
    UserSubscription,
    UserSubscriptionResponse,
    WebhookResponse,
)
from services.subscription_service import SubscriptionService
from utils.exceptions import BusinessLogicError, ResourceNotFoundError, ValidationError
from utils.response import create_model_response


def _transaction() -> TransactionData:
    return TransactionData(
        provider=SubscriptionProvider.APPLE,
        transaction_id="trans-1",
        product_id="prod-1",
        purchase_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        expiration_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
        environment=StoreEnvironment.SANDBOX,
    )


def _validation_result(
    *,
    is_valid: bool = True,
    status: ReceiptValidationStatus = ReceiptValidationStatus.VALID,
) -> ReceiptValidationResult:
    return ReceiptValidationResult(
        is_valid=is_valid,
        status=status,
        transaction_data=_transaction(),
        error_message=None,
        retry_after=None,
    )


def _service() -> tuple[SubscriptionService, Mock, Mock]:
    service = SubscriptionService.__new__(SubscriptionService)
    service.subscription_repository = Mock()
    service.apple_storekit_service = Mock()
    service.find_user_id_by_transaction_id = Mock()
    return service, service.subscription_repository, service.apple_storekit_service


def test_validate_and_create_subscription_success() -> None:
    service, repository, apple = _service()
    apple.validate_transaction.return_value = _validation_result()
    repository.create_subscription.return_value = True

    service.validate_and_create_subscription("user-1", _transaction())

    repository.create_subscription.assert_called_once()


def test_validate_and_create_subscription_invalid() -> None:
    service, repository, apple = _service()
    apple.validate_transaction.return_value = _validation_result(
        is_valid=False, status=ReceiptValidationStatus.EXPIRED
    )

    with pytest.raises(ValidationError):
        service.validate_and_create_subscription("user-1", _transaction())


def test_handle_renewal_webhook_requires_user() -> None:
    service, _, _ = _service()
    service.find_user_id_by_transaction_id.return_value = None
    with pytest.raises(ResourceNotFoundError):
        service.handle_renewal_webhook("trans-1")


def test_handle_renewal_webhook_invokes_internal() -> None:
    service, _, _ = _service()
    service.find_user_id_by_transaction_id.return_value = "user-1"
    service._handle_renewal_with_validation = Mock()

    service.handle_renewal_webhook("trans-1")
    service._handle_renewal_with_validation.assert_called_once_with("user-1", "trans-1")


def test_handle_renewal_with_validation_updates_subscription() -> None:
    service, repository, apple = _service()
    subscription = UserSubscription(
        user_id="user-1",
        provider=SubscriptionProvider.APPLE,
        transaction_id="old",
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=None,
    )
    repository.get_active_subscription.return_value = subscription
    new_data = _transaction().model_copy(
        update={"expiration_date": datetime(2025, 3, 1, tzinfo=timezone.utc)}
    )
    apple.validate_transaction.return_value = _validation_result()
    apple.validate_transaction.return_value.transaction_data = new_data
    repository.update_subscription.return_value = True

    service._handle_renewal_with_validation("user-1", "trans-new")

    repository.update_subscription.assert_called_once()
    updated = repository.update_subscription.call_args.args[0]
    assert updated.transaction_id == "trans-new"
    assert updated.end_date == new_data.expiration_date


def test_handle_renewal_with_validation_bad_validation() -> None:
    service, repository, apple = _service()
    repository.get_active_subscription.return_value = UserSubscription(
        user_id="user-1",
        provider=SubscriptionProvider.APPLE,
        transaction_id="old",
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    apple.validate_transaction.return_value = _validation_result(
        is_valid=False, status=ReceiptValidationStatus.INVALID
    )
    with pytest.raises(BusinessLogicError):
        service._handle_renewal_with_validation("user-1", "trans-new")


def test_handle_cancellation_webhook() -> None:
    service, repository, _ = _service()
    service.find_user_id_by_transaction_id.return_value = "user-1"
    repository.cancel_subscription.return_value = True
    service.handle_cancellation_webhook("trans")
    repository.cancel_subscription.assert_called_once_with("user-1")


def test_handle_failed_payment_updates_status() -> None:
    service, repository, _ = _service()
    subscription = UserSubscription(
        user_id="user-1",
        provider=SubscriptionProvider.APPLE,
        transaction_id="old",
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=None,
    )
    repository.get_active_subscription.return_value = subscription
    repository.update_subscription.return_value = True
    service._handle_failed_payment("user-1")
    repository.update_subscription.assert_called_once()


def test_find_user_id_by_transaction_id() -> None:
    service = SubscriptionService.__new__(SubscriptionService)
    service.subscription_repository = Mock()
    service.subscription_repository.find_by_transaction_id.return_value = SimpleNamespace(user_id="user-1")
    assert service.find_user_id_by_transaction_id("trans") == "user-1"


def test_user_subscription_response_serialization_matches_api_contract() -> None:
    subscription = UserSubscription(
        user_id="user-1",
        provider=SubscriptionProvider.APPLE,
        transaction_id="trans-1",
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )
    response = subscription.to_api_response()

    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["provider"] == SubscriptionProvider.APPLE.value
    assert body["status"] == SubscriptionStatus.ACTIVE.value
    datetime.fromisoformat(body["start_date"])
    datetime.fromisoformat(body["end_date"])


def test_receipt_validation_result_serialization_matches_api_contract() -> None:
    result = ReceiptValidationResult(
        is_valid=True,
        status=ReceiptValidationStatus.VALID,
        transaction_data=_transaction(),
        error_message=None,
        retry_after=None,
    )

    envelope = create_model_response(result)
    body = json.loads(envelope["body"])

    assert body["status"] == ReceiptValidationStatus.VALID.value
    assert body["transaction_data"]["provider"] == SubscriptionProvider.APPLE.value
    assert isinstance(body["is_valid"], bool)


def test_webhook_response_serialization_matches_api_contract() -> None:
    response = WebhookResponse(success=True, message="Processed")
    envelope = create_model_response(response)
    body = json.loads(envelope["body"])

    assert body["success"] is True
    assert body["message"] == "Processed"
