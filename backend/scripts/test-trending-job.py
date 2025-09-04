#!/usr/bin/env python3
"""
Test script for the trending job Lambda function.
This script can be used to manually trigger the trending job for testing.
"""

import json
import boto3
import sys
import os
from datetime import datetime

def test_trending_job(environment="dev"):
    """Test the trending job Lambda function."""

    # Create Lambda client
    lambda_client = boto3.client('lambda')

    # Function name
    function_name = f"lingible-trending-job-{environment}"

    # Test payload
    test_payload = {
        "job_type": "gen_z_slang_analysis",
        "source": "bedrock_ai",
        "parameters": {
            "model": "anthropic.claude-3-haiku-20240307-v1:0",
            "max_terms": 20,
            "categories": ["slang", "meme", "expression", "hashtag", "phrase"],
        },
        "scheduled_at": datetime.now().isoformat(),
    }

    print(f"Testing trending job: {function_name}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print("-" * 50)

    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps(test_payload)
        )

        # Parse the response
        response_payload = json.loads(response['Payload'].read())

        print("Response:")
        print(json.dumps(response_payload, indent=2))

        if response['StatusCode'] == 200:
            print("\n✅ Trending job completed successfully!")
        else:
            print(f"\n❌ Trending job failed with status: {response['StatusCode']}")

    except Exception as e:
        print(f"\n❌ Error invoking trending job: {str(e)}")
        return False

    return True

def main():
    """Main function."""
    environment = sys.argv[1] if len(sys.argv) > 1 else "dev"

    print(f"🚀 Testing Lingible Trending Job - Environment: {environment}")
    print("=" * 60)

    success = test_trending_job(environment)

    if success:
        print("\n🎉 Test completed successfully!")
        print("\nNext steps:")
        print("1. Check the DynamoDB trending table for new terms")
        print("2. Test the /trending API endpoint")
        print("3. Verify the scheduled job runs daily at 6 AM UTC")
    else:
        print("\n💥 Test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
