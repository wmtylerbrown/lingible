#!/bin/bash

# Amplify Configuration Setup Script
# This script automatically sets up the correct Amplify configuration based on build configuration

echo "🔧 Setting up Amplify configuration..."

# Navigate to the project directory
cd "$(dirname "$0")/../Lingible"

# Check if we're in a build context (Xcode sets CONFIGURATION)
if [ -n "$CONFIGURATION" ]; then
    echo "📱 Build Configuration: $CONFIGURATION"
    
    if [ "$CONFIGURATION" = "Debug" ]; then
        echo "🔧 Using development configuration..."
        cp amplify_outputs-dev.json amplify_outputs.json
        echo "✅ Development configuration set up"
        echo "🔗 User Pool ID: us-east-1_65YoJgNVi"
    elif [ "$CONFIGURATION" = "Release" ]; then
        echo "🔧 Using production configuration..."
        cp amplify_outputs-prod.json amplify_outputs.json
        echo "✅ Production configuration set up"
        echo "🔗 User Pool ID: us-east-1_ENGYDDFRb"
    else
        echo "⚠️  Unknown configuration: $CONFIGURATION"
        echo "🔧 Defaulting to development configuration..."
        cp amplify_outputs-dev.json amplify_outputs.json
    fi
else
    # Manual execution - default to development
    echo "🔧 Manual execution - using development configuration..."
    cp amplify_outputs-dev.json amplify_outputs.json
    echo "✅ Development configuration set up"
    echo "💡 To use production: CONFIGURATION=Release $0"
fi

echo "🎯 Configuration complete!"
