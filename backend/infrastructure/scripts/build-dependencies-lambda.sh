#!/bin/bash

set -e

echo "🐳 Building Lambda dependencies for Amazon Linux runtime..."

# Create a temporary directory for the build
BUILD_DIR=$(mktemp -d)
echo "📁 Build directory: $BUILD_DIR"

# Copy requirements file to build directory
cp lambda-layer-requirements.txt "$BUILD_DIR/requirements.txt"

# Create python directory
mkdir -p "$BUILD_DIR/python"

# Install dependencies with platform-specific flags for Lambda
echo "📦 Installing Python dependencies for Lambda runtime..."
pip3 install -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR/python" \
  --platform manylinux2014_x86_64 \
  --target-platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --no-deps

# Copy built dependencies to the lambda-dependencies-layer directory
echo "📦 Copying built dependencies..."
rm -rf lambda-dependencies-layer/python
mkdir -p lambda-dependencies-layer/python
cp -r "$BUILD_DIR/python"/* lambda-dependencies-layer/python/

# Clean up
rm -rf "$BUILD_DIR"

echo "✅ Dependencies built successfully for Lambda runtime!"
