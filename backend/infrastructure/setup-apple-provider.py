#!/usr/bin/env python3
"""Setup script for Apple Identity Provider configuration."""

import json
import os
from pathlib import Path


def get_apple_credentials():
    """Interactive setup for Apple Identity Provider credentials."""
    print("🍎 Apple Identity Provider Setup")
    print("=" * 40)
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


def update_cognito_stack(credentials):
    """Update the Cognito stack with Apple credentials."""
    cognito_stack_path = Path("constructs/cognito_stack.py")

    if not cognito_stack_path.exists():
        print(f"❌ Error: {cognito_stack_path} not found!")
        return False

    # Read the current file
    with open(cognito_stack_path, 'r') as f:
        content = f.read()

    # Replace placeholder values
    content = content.replace("com.lingible.lingible", credentials["client_id"])
    content = content.replace("YOUR_APPLE_TEAM_ID", credentials["team_id"])
    content = content.replace("YOUR_APPLE_KEY_ID", credentials["key_id"])
    content = content.replace("YOUR_APPLE_PRIVATE_KEY", f'"""{credentials["private_key"]}"""')

    # Write back to file
    with open(cognito_stack_path, 'w') as f:
        f.write(content)

    print(f"✅ Updated {cognito_stack_path}")
    return True


def create_secrets_file(credentials):
    """Create a secrets file for sensitive data (optional)."""
    secrets_path = Path("apple-secrets.json")

    secrets_data = {
        "apple_identity_provider": {
            "client_id": credentials["client_id"],
            "team_id": credentials["team_id"],
            "key_id": credentials["key_id"],
            "private_key": credentials["private_key"]
        }
    }

    with open(secrets_path, 'w') as f:
        json.dump(secrets_data, f, indent=2)

    print(f"✅ Created {secrets_path} (add this to .gitignore)")
    return True


def main():
    """Main setup function."""
    print("🚀 Apple Identity Provider Configuration")
    print("=" * 50)
    print()

    # Check if we're in the right directory
    if not Path("constructs/cognito_stack.py").exists():
        print("❌ Please run this script from the infrastructure directory")
        return

    # Get credentials
    credentials = get_apple_credentials()
    if not credentials:
        return

    print()
    print("📝 Updating Cognito stack...")

    # Update the Cognito stack
    if update_cognito_stack(credentials):
        print("✅ Cognito stack updated successfully!")
    else:
        print("❌ Failed to update Cognito stack")
        return

    # Create secrets file
    print()
    print("🔐 Creating secrets file...")
    create_secrets_file(credentials)

    print()
    print("🎉 Apple Identity Provider setup complete!")
    print()
    print("📋 Next steps:")
    print("1. Add 'apple-secrets.json' to your .gitignore file")
    print("2. Deploy your infrastructure: python deploy.py")
    print("3. Test Sign in with Apple in your mobile app")
    print()
    print("📚 Documentation:")
    print("- Apple Developer Console: https://developer.apple.com")
    print("- AWS Cognito Apple Provider: https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-identity-provider-apple.html")


if __name__ == "__main__":
    main()
