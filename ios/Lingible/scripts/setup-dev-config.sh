#!/bin/bash

# Development Configuration Setup Script
# This script copies the development Amplify configuration to the default location

echo "🔧 Setting up development configuration..."

# Navigate to the project directory
cd "$(dirname "$0")/../Lingible"

# Copy development config to default location
cp amplify_outputs-dev.json amplify_outputs.json

echo "✅ Development configuration set up successfully"
echo "📱 App will now use development Cognito User Pool"
echo "🔗 User Pool ID: us-east-1_65YoJgNVi"
echo "🌐 OAuth Domain: lingible-dev.auth.us-east-1.amazoncognito.com"
