#!/usr/bin/env python3
"""Test script for receipt validation with official Apple and Google SDKs."""

import json
import sys
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, 'src')

from src.models.subscriptions import (
    ReceiptValidationRequest,
    SubscriptionProvider,
    ReceiptValidationStatus
)
from src.services.receipt_validation_service import ReceiptValidationService


def test_apple_receipt_validation():
    """Test Apple receipt validation with sample data."""
    print("🍎 Testing Apple Receipt Validation...")

    # Sample Apple receipt data (this would come from the iOS app)
    sample_receipt_data = "base64_encoded_receipt_data_here"

    request = ReceiptValidationRequest(
        provider=SubscriptionProvider.APPLE,
        receipt_data=sample_receipt_data,
        transaction_id="test_transaction_123",
        user_id="test_user_456"
    )

    service = ReceiptValidationService()

    try:
        result = service.validate_receipt(request)
        print(f"✅ Apple validation result: {result.status.value}")
        print(f"   Valid: {result.is_valid}")
        print(f"   Product ID: {result.product_id}")
        print(f"   Environment: {result.environment}")
        if result.error_message:
            print(f"   Error: {result.error_message}")
    except Exception as e:
        print(f"❌ Apple validation error: {e}")


def test_google_receipt_validation():
    """Test Google Play receipt validation with sample data."""
    print("\n🤖 Testing Google Play Receipt Validation...")

    # Sample Google Play receipt data (this would come from the Android app)
    sample_receipt_data = json.dumps({
        "packageName": "com.yourapp.genztranslator",
        "productId": "premium_monthly",
        "purchaseToken": "sample_purchase_token_123",
        "orderId": "order_123456"
    })

    request = ReceiptValidationRequest(
        provider=SubscriptionProvider.GOOGLE,
        receipt_data=sample_receipt_data,
        transaction_id="test_transaction_456",
        user_id="test_user_789"
    )

    service = ReceiptValidationService()

    try:
        result = service.validate_receipt(request)
        print(f"✅ Google validation result: {result.status.value}")
        print(f"   Valid: {result.is_valid}")
        print(f"   Product ID: {result.product_id}")
        print(f"   Environment: {result.environment}")
        if result.error_message:
            print(f"   Error: {result.error_message}")
    except Exception as e:
        print(f"❌ Google validation error: {e}")


def test_error_handling():
    """Test error handling with invalid data."""
    print("\n🚨 Testing Error Handling...")

    # Test with invalid JSON for Google
    invalid_receipt_data = "invalid_json_data"

    request = ReceiptValidationRequest(
        provider=SubscriptionProvider.GOOGLE,
        receipt_data=invalid_receipt_data,
        transaction_id="test_transaction_error",
        user_id="test_user_error"
    )

    service = ReceiptValidationService()

    try:
        result = service.validate_receipt(request)
        print(f"✅ Error handling result: {result.status.value}")
        print(f"   Valid: {result.is_valid}")
        print(f"   Error: {result.error_message}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Run all receipt validation tests."""
    print("🧪 Receipt Validation Service Test Suite")
    print("=" * 50)

    # Test Apple validation
    test_apple_receipt_validation()

    # Test Google validation
    test_google_receipt_validation()

    # Test error handling
    test_error_handling()

    print("\n" + "=" * 50)
    print("✅ Test suite completed!")
    print("\n📝 Notes:")
    print("- Apple validation requires real receipt data from iOS app")
    print("- Google validation requires real purchase token from Android app")
    print("- Service account credentials needed for Google Play API")
    print("- Apple shared secret needed for App Store validation")


if __name__ == "__main__":
    main()
