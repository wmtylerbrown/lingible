"""Apple webhook handler for subscription updates."""

from typing import Optional
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import event_parser

from models.events import AppleWebhookEvent
from models.subscriptions import WebhookResponse, StoreEnvironment
from models.users import UserTier
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from utils.decorators import api_handler
from utils.smart_logger import SmartLogger
from utils.envelopes import AppleWebhookEnvelope
from utils.exceptions import BusinessLogicError, ValidationError, SystemError

# Initialize services at module level for Lambda container reuse
subscription_service = SubscriptionService()
user_service = UserService()
logger = SmartLogger()


@event_parser(model=AppleWebhookEvent, envelope=AppleWebhookEnvelope)
@api_handler()
def handler(event: AppleWebhookEvent, context: LambdaContext) -> WebhookResponse:
    """
    Handle Apple App Store Server Notifications.

    According to Apple's documentation, we must:
    1. Verify the JWS signature
    2. Respond with HTTP 200 immediately upon receipt
    3. Process the notification asynchronously
    """
    try:
        # The request body contains the signed JWS payload from Apple
        signed_payload = event.request_body.signed_payload

        # Verify JWS signature and decode payload using Apple SDK
        decoded_payload = subscription_service.verify_and_decode_apple_webhook(
            signed_payload
        )
        if not decoded_payload:
            raise ValidationError(
                "Invalid JWS signature or payload",
                details={"signed_payload_length": len(signed_payload)},
            )

        # Extract notification information from Apple SDK decoded payload
        notification_type = decoded_payload.notificationType
        notification_uuid = decoded_payload.notificationUUID
        subtype = decoded_payload.subtype

        # Log the notification for processing
        logger.log_business_event(
            "apple_webhook_received",
            {
                "notification_type": str(notification_type),
                "notification_uuid": str(notification_uuid),
                "subtype": str(subtype),
            },
        )

        # Process the notification using Apple SDK data
        _process_notification(decoded_payload)

        # If we get here, processing succeeded - return success response
        return WebhookResponse(
            success=True, message="Notification processed successfully"
        )

    except Exception as e:
        # Log the error and re-raise so the decorator can handle it properly
        logger.log_error(e, {"operation": "apple_webhook_handler"})
        raise


def _process_notification(decoded_payload) -> None:
    """
    Process the notification using Apple SDK models.

    This function handles the actual business logic for different
    notification types.

    Args:
        decoded_payload: ResponseBodyV2DecodedPayload from Apple SDK

    Raises:
        BusinessLogicError: If notification processing fails
    """
    try:
        notification_type = str(decoded_payload.notificationType)
        data = decoded_payload.data

        # Extract transaction information from Apple's data
        transaction_id = _extract_transaction_id_from_data(data)

        # Some notifications don't require transaction processing
        if not transaction_id:
            # For notifications that don't need transaction processing, return success
            if any(
                no_transaction_type in notification_type
                for no_transaction_type in [
                    "DID_CHANGE_RENEWAL_STATUS",
                    "DID_CHANGE_RENEWAL_PREF",
                    "DID_FAIL_TO_RENEW",  # Some failure notifications might not have transaction info
                ]
            ):
                logger.log_business_event(
                    "webhook_no_transaction_required",
                    {"notification_type": notification_type},
                )
                # No processing needed for these notification types
                return
            else:
                # For notifications that should have transaction info, this is an error
                raise ValidationError(
                    f"Missing required transaction ID for notification type: {notification_type}",
                    details={"notification_type": notification_type},
                )

        # Handle different Apple notification types using our existing business logic
        if "DID_RENEW" in notification_type:
            subscription_service.handle_renewal_webhook(transaction_id)

        elif "DID_CANCEL" in notification_type:
            # Step 1: Cancel subscription (raises exception if fails)
            subscription_service.handle_cancellation_webhook(transaction_id)

            # Step 2: Downgrade user tier to FREE
            # If handle_cancellation_webhook succeeded, we know the user exists
            user_id = subscription_service.find_user_id_by_transaction_id(
                transaction_id
            )
            assert (
                user_id is not None
            ), f"User ID should exist after successful cancellation for transaction {transaction_id}"
            user_service.downgrade_user_tier(user_id, UserTier.FREE)

        elif "DID_FAIL_TO_RENEW" in notification_type:
            # Step 1: Mark subscription as expired (raises exception if fails)
            subscription_service.handle_failed_payment_webhook(transaction_id)

            # Step 2: Downgrade user tier to FREE
            # If handle_failed_payment_webhook succeeded, we know the user exists
            user_id = subscription_service.find_user_id_by_transaction_id(
                transaction_id
            )
            assert (
                user_id is not None
            ), f"User ID should exist after successful payment failure handling for transaction {transaction_id}"
            user_service.downgrade_user_tier(user_id, UserTier.FREE)

        elif "SUBSCRIBED" in notification_type:
            # New subscription - handle like a renewal for now
            subscription_service.handle_renewal_webhook(transaction_id)

        elif (
            "DID_CHANGE_RENEWAL_STATUS" in notification_type
            or "DID_CHANGE_RENEWAL_PREF" in notification_type
        ):
            # Status/preference changes - log but don't fail
            logger.log_business_event(
                "renewal_change_processed", {"notification_type": notification_type}
            )
            # No processing needed for these types

        else:
            # Unknown notification type - log but don't fail
            logger.log_business_event(
                "unknown_notification_type", {"notification_type": notification_type}
            )
            # No processing needed for unknown types

    except (ValidationError, BusinessLogicError):
        # Re-raise validation and business logic errors as-is
        raise
    except Exception as e:
        # Log unexpected errors and re-raise as SystemError
        logger.log_error(e, {"operation": "process_notification"})
        raise SystemError(
            f"Unexpected error processing notification: {str(e)}",
            details={"original_error": str(e)},
        )


def _extract_transaction_id_from_data(data) -> Optional[str]:
    """
    Extract transaction ID from Apple's webhook data.

    Args:
        data: Data object from Apple's decoded webhook payload

    Returns:
        str: Transaction ID or None if not found
    """
    try:
        # The data object contains signed transaction info
        # We need to decode the signed transaction to get the transaction ID
        if hasattr(data, "signed_transaction_info") and data.signed_transaction_info:
            # Use Apple's SDK to decode the signed transaction
            verifier = (
                subscription_service.apple_storekit_service._get_signed_data_verifier(
                    StoreEnvironment.PRODUCTION
                )
            )

            # Decode the signed transaction to get the transaction ID
            decoded_transaction = verifier.verify_and_decode_signed_transaction(
                data.signed_transaction_info
            )
            return decoded_transaction.transactionId

        elif hasattr(data, "signed_renewal_info") and data.signed_renewal_info:
            # Some notifications might only have renewal info
            # For renewal info, we might need to extract the original transaction ID differently
            logger.log_business_event(
                "webhook_renewal_info_only",
                {"message": "Webhook contains renewal info but no transaction info"},
            )
            # TODO: Extract transaction ID from renewal info if possible
            return None

        else:
            logger.log_business_event(
                "webhook_no_signed_data",
                {
                    "message": "Webhook data contains no signed transaction or renewal info"
                },
            )
            return None

    except Exception as e:
        logger.log_error(e, {"operation": "extract_transaction_id"})
        return None
