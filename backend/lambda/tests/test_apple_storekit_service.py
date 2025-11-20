from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from appstoreserverlibrary.api_client import APIException
from models.config import AppleConfig
from models.subscriptions import (
    ReceiptValidationRequest,
    ReceiptValidationStatus,
    StoreEnvironment,
    SubscriptionProvider,
    TransactionData,
)
from services.apple_storekit_service import AppleStoreKitService
from utils.exceptions import ValidationError


def _apple_config() -> AppleConfig:
    return AppleConfig(
        private_key=b"-----BEGIN PRIVATE KEY-----\nkey\n-----END PRIVATE KEY-----",
        key_id="ABC123",
        issuer_id="issuer",
        bundle_id="com.test.app",
    )


def _transaction_data() -> TransactionData:
    return TransactionData(
        provider=SubscriptionProvider.APPLE,
        transaction_id="trans-123",
        product_id="prod",
        purchase_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        expiration_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        environment=StoreEnvironment.SANDBOX,
    )


@pytest.fixture
def service() -> AppleStoreKitService:
    with patch("services.apple_storekit_service.get_config_service") as config_service_cls:
        config_service = config_service_cls.return_value
        config_service.get_config.return_value = _apple_config()
        with patch("services.apple_storekit_service.SignedDataVerifier"):
            yield AppleStoreKitService()


def test_validate_transaction_rejects_non_apple(service: AppleStoreKitService) -> None:
    request = ReceiptValidationRequest(
        transaction_data=_transaction_data().model_copy(update={"provider": SubscriptionProvider.GOOGLE}),
        user_id="user-1",
    )
    result = service.validate_transaction(request)
    assert result.is_valid is False
    assert result.status == ReceiptValidationStatus.RETRYABLE_ERROR


def test_validate_transaction_success(service: AppleStoreKitService) -> None:
    with patch.object(service, "_get_transaction_info") as info_mock:
        info_mock.return_value = SimpleNamespace(signedTransactionInfo="payload")
        result = service.validate_transaction(
            ReceiptValidationRequest(transaction_data=_transaction_data(), user_id="user-1")
        )
    assert result.is_valid is True
    assert result.status == ReceiptValidationStatus.VALID


def test_validate_transaction_handles_api_exception(service: AppleStoreKitService) -> None:
    class FakeAPIException(APIException):
        def __init__(self, msg: str, http_status_code: int) -> None:
            super().__init__(msg)
            self.http_status_code = http_status_code

    with patch.object(service, "_get_transaction_info") as info_mock:
        info_mock.side_effect = FakeAPIException("not found", 404)
        result = service.validate_transaction(
            ReceiptValidationRequest(transaction_data=_transaction_data(), user_id="user-1")
        )
    assert result.is_valid is False
    assert result.status == ReceiptValidationStatus.INVALID_TRANSACTION


def test_get_transaction_info_returns_none_on_404(service: AppleStoreKitService) -> None:
    fake_client = MagicMock()
    exc = APIException("not found")
    exc.http_status_code = 404
    fake_client.get_transaction_info.side_effect = exc
    with patch.object(service, "_get_client", return_value=fake_client):
        result = service._get_transaction_info("trans", StoreEnvironment.PRODUCTION)
    assert result is None


def test_verify_and_decode_webhook_uses_verifier() -> None:
    with patch("services.apple_storekit_service.get_config_service") as config_service_cls, \
         patch("services.apple_storekit_service.SignedDataVerifier") as verifier_cls:
        config_service = config_service_cls.return_value
        config_service.get_config.return_value = _apple_config()
        verifier = verifier_cls.return_value
        verifier.verify_and_decode_notification.return_value = "decoded"
        service = AppleStoreKitService()
        result = service.verify_and_decode_webhook("payload", StoreEnvironment.SANDBOX)
    assert result == "decoded"
    verifier.verify_and_decode_notification.assert_called_once()


def test_verify_webhook_signature_returns_false_on_error(service: AppleStoreKitService) -> None:
    with patch.object(service, "verify_and_decode_webhook", side_effect=RuntimeError("boom")):
        assert service.verify_webhook_signature("payload") is False


def test_get_client_builds_api_client(service: AppleStoreKitService) -> None:
    with patch("services.apple_storekit_service.AppStoreServerAPIClient") as client_cls:
        client = client_cls.return_value
        result = service._get_client(StoreEnvironment.SANDBOX)
    client_cls.assert_called_once()
    assert result is client


def test_get_client_raises_validation_error(service: AppleStoreKitService) -> None:
    with patch("services.apple_storekit_service.AppStoreServerAPIClient", side_effect=RuntimeError("boom")):
        with pytest.raises(ValidationError):
            service._get_client(StoreEnvironment.SANDBOX)


def test_extract_transaction_data_decodes_payload(service: AppleStoreKitService) -> None:
    payload = json.dumps({"id": "123"}).encode("utf-8")
    encoded = base64.b64encode(payload).decode("utf-8")
    assert service._extract_transaction_data(encoded) == {"id": "123"}


def test_create_validated_transaction_data_falls_back(service: AppleStoreKitService) -> None:
    original = _transaction_data()
    result = service._create_validated_transaction_data(SimpleNamespace(), original)
    assert result.transaction_id == original.transaction_id


def test_parse_apple_date_handles_variants(service: AppleStoreKitService) -> None:
    assert service._parse_apple_date(1700000000000) is not None
    assert service._parse_apple_date("2025-01-01T00:00:00Z") is not None
    assert service._parse_apple_date({"bad": "value"}) is None


def test_load_root_certificates_returns_bytes(service: AppleStoreKitService) -> None:
    certs = service._load_apple_root_certificates()
    assert len(certs) >= 1
    assert isinstance(certs[0], bytes)
