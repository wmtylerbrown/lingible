#!/usr/bin/env python3
"""Deployment script for GenZ Translation App infrastructure."""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    print(f"   Running: {command}")

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"   Error: {e.stderr.strip()}")
        sys.exit(1)


def main():
    """Main deployment function."""
    print("🚀 GenZ Translation App Infrastructure Deployment")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Please run this script from the infrastructure directory")
        sys.exit(1)

    # Check if CDK is installed
    try:
        subprocess.run(["cdk", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ CDK CLI not found. Please install it first:")
        print("   npm install -g aws-cdk")
        sys.exit(1)

    # Install dependencies
    run_command("pip install -r requirements.txt", "Installing CDK dependencies")

    # Bootstrap CDK (if needed)
    print("🔄 Checking if CDK bootstrap is needed...")
    try:
        subprocess.run(["cdk", "bootstrap"], check=True, capture_output=True)
        print("✅ CDK bootstrap completed")
    except subprocess.CalledProcessError:
        print("ℹ️  CDK bootstrap already completed or not needed")

    # Deploy the stack
    run_command("cdk deploy --require-approval never", "Deploying infrastructure")

    print("\n🎉 Deployment completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Update your mobile app with the new API Gateway URL")
    print("   2. Configure Cognito User Pool in your app")
    print("   3. Test the API endpoints")
    print("   4. Set up monitoring alerts (SNS subscriptions)")

    # Show outputs
    print("\n📊 Getting stack outputs...")
    run_command("cdk list", "Listing deployed stacks")


if __name__ == "__main__":
    main()
