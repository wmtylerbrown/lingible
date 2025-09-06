#!/bin/bash

# Production Configuration Setup Script
# This script copies the production Amplify configuration to the default location

echo "🔧 Setting up production configuration..."

# Navigate to the project directory
cd "$(dirname "$0")/../Lingible"

# Copy production config to default location
cp amplify_outputs-prod.json amplify_outputs.json

echo "✅ Production configuration set up successfully"
echo "📱 App will now use production Cognito User Pool"
echo "🔗 User Pool ID: us-east-1_ENGYDDFRb"
echo "🌐 OAuth Domain: lingible-prod.auth.us-east-1.amazoncognito.com"
