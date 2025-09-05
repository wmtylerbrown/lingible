#!/bin/sh

# Xcode Cloud Post-Clone Script
# This script runs after the repository is cloned but before the build starts

echo "🚀 Starting Xcode Cloud build for Lingible..."

# Set environment variables for the build
export DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"

# Navigate to the iOS project directory
cd ios/Lingible

echo "📱 Building iOS app with bundle ID: com.lingible.lingible.dev"

# The actual build will be handled by Xcode Cloud's build system
# This script is for any pre-build setup we might need

echo "✅ Post-clone script completed successfully"
