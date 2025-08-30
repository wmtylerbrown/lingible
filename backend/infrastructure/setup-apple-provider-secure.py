#!/usr/bin/env python3
"""Secure setup script for Apple Identity Provider using AWS Secrets Manager."""

import json
import boto3
import sys
from pathlib import Path


def get_apple_credentials():
    """Interactive setup for Apple Identity Provider credentials."""
    print("🍎 Secure Apple Identity Provider Setup")
    print("=" * 45)
    print()

    print("This will store your Apple credentials securely in AWS Secrets Manager.")
    print("Your private key will NOT be stored in code or version control.")
    print()

    print("Please provide the following information from your Apple Developer Console:")
    print()

    # Get credentials from user
    client_id = input("App ID (e.g., com.lingible.lingible): ").strip()
    team_id = input("Team ID (found in Membership section): ").strip()
    key_id = input("Key ID (from the private key you created): ").strip()

    print()
    print("Private Key (PEM format):")
    print("Paste your private key content below (press Ctrl+D when done):")

    private_key_lines = []
    try:
        while True:
            line = input()
            private_key_lines.append(line)
    except EOFError:
        pass

    private_key = "\n".join(private_key_lines)

    # Validate inputs
    if not all([client_id, team_id, key_id, private_key]):
        print("❌ Error: All fields are required!")
        return None

    if not private_key.startswith("-----BEGIN PRIVATE KEY-----"):
        print("❌ Error: Private key should be in PEM format!")
        return None

    return {
        "client_id": client_id,
        "team_id": team_id,
        "key_id": key_id,
        "private_key": private_key
    }


def store_in_secrets_manager(credentials):
    """Store Apple credentials in AWS Secrets Manager."""
    try:
        secrets_client = boto3.client('secretsmanager')

        secret_name = "genz-app/apple-identity-provider"

        # Create the secret value
        secret_value = {
            "client_id": credentials["client_id"],
            "team_id": credentials["team_id"],
            "key_id": credentials["key_id"],
            "private_key": credentials["private_key"]
        }

        try:
            # Try to update existing secret
            secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_value)
            )
            print(f"✅ Updated existing secret: {secret_name}")
        except secrets_client.exceptions.ResourceNotFoundException:
            # Create new secret
            secrets_client.create_secret(
                Name=secret_name,
                Description="Apple Identity Provider credentials for Sign in with Apple",
                SecretString=json.dumps(secret_value),
                Tags=[
                    {
                        'Key': 'Application',
                        'Value': 'GenZTranslationApp'
                    },
                    {
                        'Key': 'Environment',
                        'Value': 'production'
                    }
                ]
            )
            print(f"✅ Created new secret: {secret_name}")

        return True

    except Exception as e:
        print(f"❌ Error storing secret: {e}")
        return False


def create_secure_cognito_stack():
    """Create a secure version of the Cognito stack."""
    cognito_stack_path = Path("constructs/cognito_stack.py")
    secure_stack_path = Path("constructs/cognito_stack_secure.py")

    if not cognito_stack_path.exists():
        print(f"❌ Error: {cognito_stack_path} not found!")
        return False

    # Copy the secure version
    if secure_stack_path.exists():
        # Backup existing file
        backup_path = Path("constructs/cognito_stack_backup.py")
        if cognito_stack_path.exists():
            cognito_stack_path.rename(backup_path)
            print(f"✅ Backed up existing stack to {backup_path}")

        # Copy secure version
        import shutil
        shutil.copy(secure_stack_path, cognito_stack_path)
        print(f"✅ Updated {cognito_stack_path} with secure version")

        return True
    else:
        print(f"❌ Error: {secure_stack_path} not found!")
        return False


def main():
    """Main setup function."""
    print("🚀 Secure Apple Identity Provider Configuration")
    print("=" * 55)
    print()

    # Check if we're in the right directory
    if not Path("constructs/cognito_stack.py").exists():
        print("❌ Please run this script from the infrastructure directory")
        return

    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
        print("✅ AWS credentials verified")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("Please run: aws configure")
        return

    # Get credentials
    credentials = get_apple_credentials()
    if not credentials:
        return

    print()
    print("🔐 Storing credentials in AWS Secrets Manager...")

    # Store in Secrets Manager
    if store_in_secrets_manager(credentials):
        print("✅ Credentials stored securely!")
    else:
        print("❌ Failed to store credentials")
        return

    # Update Cognito stack
    print()
    print("📝 Updating Cognito stack...")

    if create_secure_cognito_stack():
        print("✅ Cognito stack updated with secure configuration!")
    else:
        print("❌ Failed to update Cognito stack")
        return

    print()
    print("🎉 Secure Apple Identity Provider setup complete!")
    print()
    print("🔒 Security Features:")
    print("✅ Private key stored in AWS Secrets Manager (encrypted)")
    print("✅ No sensitive data in code or version control")
    print("✅ Automatic rotation capabilities")
    print("✅ Access controlled by IAM policies")
    print("✅ Audit logging enabled")
    print()
    print("📋 Next steps:")
    print("1. Deploy your infrastructure: python deploy.py")
    print("2. Test Sign in with Apple in your mobile app")
    print("3. Monitor secret access in CloudTrail")
    print()
    print("📚 Documentation:")
    print("- AWS Secrets Manager: https://docs.aws.amazon.com/secretsmanager/")
    print("- Apple Developer Console: https://developer.apple.com")


if __name__ == "__main__":
    main()
