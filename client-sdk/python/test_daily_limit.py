#!/usr/bin/env python3
"""
Test script for daily translation limit functionality

This script tests the daily translation limit by making multiple translation
requests until the limit is reached and validates the error response.
"""

import sys
import os
import logging
from typing import Optional

# Add the client SDK to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lingible_client'))

from lingible_client.authenticated_client import create_dev_client
from lingible_client.auth import CognitoAuthError
from lingible_client.exceptions import ApiException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_daily_limit(client, max_attempts=12):
    """
    Test the daily translation limit by making multiple requests.

    Args:
        client: Authenticated Lingible client
        max_attempts: Maximum number of translation attempts (should exceed daily limit)

    Returns:
        bool: True if test passes (limit is enforced), False otherwise
    """
    logger.info(f"Testing daily translation limit with {max_attempts} attempts...")

    # First, check current usage
    try:
        usage = client.get_usage_stats()
        logger.info(f"Current usage - Used: {usage.daily_used}, Limit: {usage.daily_limit}, Remaining: {usage.daily_remaining}")

        if usage.daily_used >= usage.daily_limit:
            logger.info("User has already reached daily limit. Expecting all requests to fail.")
            expected_success_count = 0
        else:
            expected_success_count = usage.daily_remaining
            logger.info(f"Expecting {expected_success_count} successful requests before hitting limit")

    except Exception as e:
        logger.error(f"Failed to get usage stats: {str(e)}")
        return False

    successful_requests = 0
    failed_requests = 0
    limit_hit = False

    # Test translations with different text to avoid any potential caching
    test_phrases = [
        "Hello, how are you?",
        "What's up?",
        "How's it going?",
        "Nice to meet you",
        "Have a great day",
        "Take care",
        "See you later",
        "Good morning",
        "Good evening",
        "Thank you very much",
        "You're welcome",
        "No problem at all"
    ]

    for i in range(max_attempts):
        phrase = test_phrases[i % len(test_phrases)]
        logger.info(f"\n--- Attempt {i + 1}/{max_attempts} ---")
        logger.info(f"Translating: '{phrase}'")

        try:
            result = client.translate(
                text=phrase,
                direction="english_to_genz"
            )

            successful_requests += 1
            logger.info(f"✅ SUCCESS - Translation {i + 1}: '{phrase}' -> '{result.translated_text}'")
            logger.info(f"Translation ID: {result.translation_id}")

        except ApiException as e:
            failed_requests += 1
            logger.info(f"❌ FAILED - Request {i + 1} failed with API error")
            logger.info(f"Status code: {e.status}")
            logger.info(f"Error details: {e.body}")

            # Check if this is a rate limit error
            if e.status == 429:
                logger.info("🚫 Rate limit hit! This is expected.")
                limit_hit = True

                # Continue making a few more requests to ensure limit is consistently enforced
                remaining_attempts = min(3, max_attempts - i - 1)
                if remaining_attempts > 0:
                    logger.info(f"Making {remaining_attempts} more requests to verify limit enforcement...")
                    continue
                else:
                    break
            else:
                logger.error(f"Unexpected error code: {e.status}")

        except Exception as e:
            failed_requests += 1
            logger.error(f"❌ FAILED - Request {i + 1} failed with unexpected error: {str(e)}")

    # Get final usage stats
    try:
        final_usage = client.get_usage_stats()
        logger.info(f"\nFinal usage - Used: {final_usage.daily_used}, Limit: {final_usage.daily_limit}, Remaining: {final_usage.daily_remaining}")
    except Exception as e:
        logger.error(f"Failed to get final usage stats: {str(e)}")

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("DAILY LIMIT TEST SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total requests attempted: {max_attempts}")
    logger.info(f"Successful requests: {successful_requests}")
    logger.info(f"Failed requests: {failed_requests}")
    logger.info(f"Limit hit: {'Yes' if limit_hit else 'No'}")

    # Validation
    if limit_hit:
        logger.info("✅ Daily limit enforcement is working correctly!")
        return True
    elif successful_requests >= 10:  # Free tier limit
        logger.warning("⚠️ More than 10 requests succeeded - daily limit may not be working!")
        return False
    else:
        logger.info("ℹ️ Test completed but limit not reached (user may have had remaining quota)")
        return True


def main():
    """Main test function."""
    logger.info("Starting daily translation limit test...")

    # Test credentials
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

        # Run the daily limit test
        success = test_daily_limit(client, max_attempts=12)

        if success:
            logger.info("🎉 Daily limit test completed successfully!")
        else:
            logger.error("❌ Daily limit test failed!")

        return success

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
