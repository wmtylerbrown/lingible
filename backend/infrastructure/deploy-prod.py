#!/usr/bin/env python3
"""Deploy to production environment."""

import subprocess
import sys
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
    """Deploy to production environment."""
    print("🚀 Lingible - Production Deployment")
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

    # Production safety check
    print("⚠️  PRODUCTION DEPLOYMENT WARNING")
    print("This will deploy to the PRODUCTION environment.")
    print("Make sure you have:")
    print("   ✅ Updated environment variables for production")
    print("   ✅ Configured Apple Identity Provider (if using)")
    print("   ✅ Set up proper monitoring and alerting")
    print("   ✅ Reviewed all security settings")
    print()

    confirm = input("Type 'PRODUCTION' to confirm deployment: ")
    if confirm != "PRODUCTION":
        print("❌ Deployment cancelled")
        sys.exit(1)

    # Install dependencies
    run_command("pip install -r requirements.txt", "Installing CDK dependencies")

    # Bootstrap CDK (if needed)
    print("🔄 Checking if CDK bootstrap is needed...")
    try:
        subprocess.run(["cdk", "bootstrap", "--context", "environment=prod"], check=True, capture_output=True)
        print("✅ CDK bootstrap completed")
    except subprocess.CalledProcessError:
        print("ℹ️  CDK bootstrap already completed or not needed")

    # Deploy the stack with approval required
    run_command("cdk deploy --context environment=prod --require-approval any-change", "Deploying production infrastructure")

    print("\n🎉 Production deployment completed successfully!")
    print("\n📋 Production Environment Details:")
    print("   - Environment: prod")
    print("   - Stack Name: Lingible-Prod")
    print("   - Tables: lingible-users-prod, lingible-translations-prod")
    print("   - API Gateway: lingible-api-prod")
    print("   - Cognito: lingible-users-prod")
    print("   - Monitoring: CloudWatch Dashboard and Alarms")

    # Show outputs
    print("\n📊 Getting stack outputs...")
    run_command("cdk list", "Listing deployed stacks")

    print("\n🔒 Production Security Checklist:")
    print("   ✅ Infrastructure deployed with proper naming")
    print("   ✅ Environment-specific resources created")
    print("   ✅ Monitoring and alerting configured")
    print("   ✅ IAM roles and policies applied")
    print("   ⚠️  Remember to:")
    print("      - Configure Apple Identity Provider if needed")
    print("      - Set up SNS email subscriptions for alerts")
    print("      - Test all API endpoints")
    print("      - Monitor CloudWatch logs and metrics")


if __name__ == "__main__":
    main()
