#!/usr/bin/env python3
"""
Test script to verify the translation endpoint response structure
This tests that the serialization fix works correctly.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Add the client SDK to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lingible_client'))

from lingible_client.authenticated_client import create_dev_client
from lingible_client.auth import CognitoAuthError
from lingible_client.models.translation_response import TranslationResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_translation_response_structure(client):
    """Test that the translation response has the correct structure."""
    logger.info("Testing translation response structure...")

    try:
        # Test translation from English to GenZ
        result: TranslationResponse = client.translate(
            text="Hello, how are you doing today?",
            direction="english_to_genz"
        )

        logger.info(f"✅ Translation successful!")
        logger.info(f"Original: {result.original_text}")
        logger.info(f"Translated: {result.translated_text}")

        # Check all required fields from OpenAPI spec
        required_fields = [
            'translation_id',
            'original_text',
            'translated_text',
            'direction',
            'created_at',
            'daily_used',
            'daily_limit',
            'tier',
            'translation_failed'
        ]

        logger.info("\nChecking response structure...")
        missing_fields = []

        # Convert to dict to check fields
        result_dict = result.to_dict()

        for field in required_fields:
            if field in result_dict:
                value = result_dict[field]
                logger.info(f"  ✅ {field}: {value} (type: {type(value).__name__})")

                # Check that tier is a string (not an enum object)
                if field == 'tier':
                    if isinstance(value, str):
                        logger.info(f"     ✓ tier is correctly serialized as string: '{value}'")
                    else:
                        logger.error(f"     ✗ tier is NOT a string, it's: {type(value)}")
                        return False

                # Check that direction is a string
                if field == 'direction':
                    if isinstance(value, str):
                        logger.info(f"     ✓ direction is correctly serialized as string: '{value}'")
                    else:
                        logger.error(f"     ✗ direction is NOT a string, it's: {type(value)}")
                        return False

            else:
                logger.error(f"  ❌ Missing required field: {field}")
                missing_fields.append(field)

        if missing_fields:
            logger.error(f"\n❌ Missing required fields: {missing_fields}")
            return False

        # Verify JSON serialization works correctly
        logger.info("\nTesting JSON serialization...")
        try:
            # Use model_dump_json() which properly handles datetime serialization
            # (to_json() in generated client SDK may not handle datetime correctly)
            if hasattr(result, 'model_dump_json'):
                json_str = result.model_dump_json()
            else:
                # Fallback: use to_dict() and serialize manually with datetime handling
                result_dict = result.to_dict()
                # Convert datetime to ISO string for JSON serialization
                for key, value in result_dict.items():
                    if isinstance(value, datetime):
                        result_dict[key] = value.isoformat()
                json_str = json.dumps(result_dict)

            parsed = json.loads(json_str)

            # Check that tier and direction are strings in JSON
            if isinstance(parsed.get('tier'), str):
                logger.info(f"  ✅ tier in JSON: '{parsed.get('tier')}' (correct type)")
            else:
                logger.error(f"  ❌ tier in JSON is not a string: {type(parsed.get('tier'))}")
                return False

            if isinstance(parsed.get('direction'), str):
                logger.info(f"  ✅ direction in JSON: '{parsed.get('direction')}' (correct type)")
            else:
                logger.error(f"  ❌ direction in JSON is not a string: {type(parsed.get('direction'))}")
                return False

            # Verify created_at is serialized as ISO string
            if 'created_at' in parsed:
                created_at = parsed.get('created_at')
                if isinstance(created_at, str):
                    logger.info(f"  ✅ created_at in JSON: '{created_at}' (correctly serialized as ISO string)")
                else:
                    logger.error(f"  ❌ created_at in JSON is not a string: {type(created_at)}")
                    return False

            logger.info("  ✅ JSON serialization successful!")

        except Exception as e:
            logger.error(f"  ❌ JSON serialization failed: {str(e)}")
            return False

        logger.info("\n✅ All response structure checks passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Translation test failed: {str(e)}")
        logger.exception(e)
        return False


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Translation Response Structure Test")
    logger.info("=" * 60)
    logger.info("Testing that translation responses have correct structure")
    logger.info("with enums serialized as strings (not enum objects)\n")

    # Test credentials (you can override these with environment variables)
    username = os.getenv('LINGIBLE_USERNAME')
    password = os.getenv('LINGIBLE_PASSWORD')

    if not username or not password:
        logger.error("Please set LINGIBLE_USERNAME and LINGIBLE_PASSWORD environment variables")
        logger.info("\nExample:")
        logger.info("  export LINGIBLE_USERNAME='your-username'")
        logger.info("  export LINGIBLE_PASSWORD='your-password'")
        logger.info("  python test_translation_fix.py")
        return False

    try:
        # Create client for development environment
        logger.info("Creating Lingible client for development environment...")
        client = create_dev_client(username, password)

        # Test authentication
        if not client.is_authenticated():
            logger.error("Client is not authenticated")
            return False

        logger.info("✅ Client authenticated successfully!\n")

        # Run test
        success = test_translation_response_structure(client)

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("🎉 TEST PASSED - Response structure is correct!")
            logger.info("=" * 60)
        else:
            logger.error("\n" + "=" * 60)
            logger.error("❌ TEST FAILED - Response structure has issues")
            logger.error("=" * 60)

        return success

    except CognitoAuthError as e:
        logger.error(f"❌ Authentication error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        logger.exception(e)
        return False
    finally:
        # Cleanup
        try:
            client.logout()
            logger.info("\nLogged out successfully")
        except:
            pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
