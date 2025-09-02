#!/usr/bin/env python3
"""
Script to reset daily usage for testing purposes

This script can be used to reset a user's daily translation count
to test the daily limit functionality from a fresh state.
"""

import sys
import os
import boto3
import json
from datetime import datetime, timezone

# Add path for imports
sys.path.insert(0, os.path.dirname(__file__))

def reset_user_daily_usage(user_id: str, region: str = 'us-east-1'):
    """
    Reset a user's daily usage count in DynamoDB.

    Args:
        user_id: The user ID to reset
        region: AWS region
    """
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name=region)

        # Get table name from environment or use default
        table_name = os.getenv('USER_USAGE_TABLE', 'lingible-dev-user-usage')
        table = dynamodb.Table(table_name)

        # Current timestamp
        now = datetime.now(timezone.utc)

        # Reset the user's daily usage
        response = table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET daily_used = :zero, updated_at = :now',
            ExpressionAttributeValues={
                ':zero': 0,
                ':now': now.isoformat()
            },
            ReturnValues='ALL_NEW'
        )

        print(f"✅ Successfully reset daily usage for user {user_id}")
        print(f"Updated record: {json.dumps(response['Attributes'], indent=2, default=str)}")
        return True

    except Exception as e:
        print(f"❌ Failed to reset daily usage: {str(e)}")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Reset user daily usage for testing')
    parser.add_argument('--user-id', required=True, help='User ID to reset')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--table', help='DynamoDB table name (overrides environment variable)')

    args = parser.parse_args()

    if args.table:
        os.environ['USER_USAGE_TABLE'] = args.table

    print(f"Resetting daily usage for user: {args.user_id}")
    print(f"Region: {args.region}")
    print(f"Table: {os.getenv('USER_USAGE_TABLE', 'lingible-dev-user-usage')}")

    success = reset_user_daily_usage(args.user_id, args.region)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
