#!/usr/bin/env python3
"""
Test script for the Lingible API Client SDK

This script demonstrates how to use the Lingible client SDK to:
1. Authenticate with Cognito
2. Check API health
3. Translate text
4. Get user profile and usage stats
"""

import sys
import os
import logging
from typing import Optional

# Add the client SDK to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lingible_client'))

from lingible_client.authenticated_client import create_dev_client
from lingible_client.auth import CognitoAuthError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_health_check(client):
    """Test the health check endpoint."""
    logger.info("Testing health check...")
    try:
        health = client.health_check()
        logger.info(f"Health check successful: {health.status}")
        logger.info(f"Service: {health.service}, Version: {health.version}")
        return True
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False


def test_translation(client):
    """Test the translation API."""
    logger.info("Testing translation API...")
    try:
        # Test translation from English to GenZ
        result = client.translate(
            text="Hello, how are you doing today?",
            direction="english_to_genz"
        )

        logger.info(f"Translation successful!")
        logger.info(f"Original: {result.original_text}")
        logger.info(f"Translated: {result.translated_text}")
        logger.info(f"Confidence: {result.confidence_score}")
        logger.info(f"Translation ID: {result.translation_id}")
        logger.info(f"Direction: {result.direction}")

        return True
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        return False


def test_user_profile(client):
    """Test getting user profile."""
    logger.info("Testing user profile...")
    try:
        profile = client.get_user_profile()
        logger.info(f"User profile retrieved successfully")
        logger.info(f"User ID: {profile.user_id}")
        logger.info(f"Email: {profile.email}")
        logger.info(f"Tier: {profile.tier}")
        logger.info(f"Status: {profile.status}")
        return True
    except Exception as e:
        logger.error(f"User profile failed: {str(e)}")
        return False


def test_usage_stats(client):
    """Test getting usage statistics."""
    logger.info("Testing usage statistics...")
    try:
        usage = client.get_usage_stats()
        logger.info(f"Usage stats retrieved successfully")
        current_period = usage.current_period
        if current_period:
            logger.info(f"Translations used: {current_period.translations_used}")
            logger.info(f"Translation limit: {current_period.translations_limit}")
            logger.info(f"Period: {current_period.period_start} to {current_period.period_end}")
        else:
            logger.info("No current period data available")
        return True
    except Exception as e:
        logger.error(f"Usage stats failed: {str(e)}")
        return False


def test_authentication_info(client):
    """Test getting authentication information."""
    logger.info("Testing authentication info...")
    try:
        user_info = client.get_user_info()
        logger.info(f"User info retrieved successfully")
        logger.info(f"User ID: {user_info.get('user_id')}")
        logger.info(f"Email: {user_info.get('email')}")
        logger.info(f"Username: {user_info.get('username')}")
        logger.info(f"Email verified: {user_info.get('email_verified')}")
        return True
    except Exception as e:
        logger.error(f"Authentication info failed: {str(e)}")
        return False


def main():
    """Main test function."""
    logger.info("Starting Lingible API Client SDK tests...")

    # Test credentials (you can override these with environment variables)
    username = os.getenv('LINGIBLE_USERNAME', '341834f8-8091-70b1-576e-ba1e9eb8e7e6')
    password = os.getenv('LINGIBLE_PASSWORD', 'TestPassword123!')

    if not username or not password:
        logger.error("Please set LINGIBLE_USERNAME and LINGIBLE_PASSWORD environment variables")
        return False

    try:
        # Create client for development environment
        logger.info("Creating Lingible client for development environment...")
        client = create_dev_client(username, password)

        # Test authentication
        if not client.is_authenticated():
            logger.error("Client is not authenticated")
            return False

        logger.info("Client authenticated successfully!")

        # Run tests
        tests = [
            ("Health Check", test_health_check),
            ("Authentication Info", test_authentication_info),
            ("User Profile", test_user_profile),
            ("Usage Stats", test_usage_stats),
            ("Translation", test_translation),
        ]

        results = []
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running test: {test_name}")
            logger.info(f"{'='*50}")

            try:
                success = test_func(client)
                results.append((test_name, success))
                if success:
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    logger.error(f"❌ {test_name} FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name} FAILED with exception: {str(e)}")
                results.append((test_name, False))

        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*50}")

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{test_name}: {status}")

        logger.info(f"\nOverall: {passed}/{total} tests passed")

        if passed == total:
            logger.info("🎉 All tests passed!")
            return True
        else:
            logger.error(f"⚠️  {total - passed} tests failed")
            return False

    except CognitoAuthError as e:
        logger.error(f"Authentication error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False
    finally:
        # Cleanup
        try:
            client.logout()
            logger.info("Logged out successfully")
        except:
            pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
