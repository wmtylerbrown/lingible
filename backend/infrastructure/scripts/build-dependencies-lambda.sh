#!/bin/bash

set -e

echo "📦 Generating requirements.txt for CDK Lambda bundling..."

# Create a temporary directory for the build
BUILD_DIR=$(mktemp -d)
echo "📁 Build directory: $BUILD_DIR"

# Create python directory
mkdir -p "$BUILD_DIR/python"

# Generate requirements.txt for CDK Docker bundling
echo "📦 Generating requirements.txt for CDK Docker bundling..."
cd ../lambda

# Export runtime dependencies to requirements.txt (no dev dependencies)
# This file will be used by CDK's Docker bundling process
poetry export --format=requirements.txt --output="requirements.txt" --without-hashes --without dev

echo "✅ Generated requirements.txt for CDK bundling"
echo "📋 CDK will use Docker to install dependencies from requirements.txt"

# Clean up
rm -rf "$BUILD_DIR"

echo "✅ Requirements.txt generated successfully for CDK Lambda bundling!"
