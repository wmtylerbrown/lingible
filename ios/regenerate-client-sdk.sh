#!/bin/bash

# iOS Client SDK Regeneration Script
# This script ensures consistent generation of the iOS client SDK from the OpenAPI spec

set -e

echo "🔄 Regenerating iOS Client SDK..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GENERATED_DIR="$SCRIPT_DIR/generated"
API_SPEC="$PROJECT_ROOT/shared/api/openapi/lingible-api.yaml"

# Check if OpenAPI spec exists
if [ ! -f "$API_SPEC" ]; then
    echo "❌ Error: OpenAPI spec not found at $API_SPEC"
    exit 1
fi

# Check if openapi-generator is installed
if ! command -v openapi-generator &> /dev/null; then
    echo "❌ Error: openapi-generator is not installed"
    echo "Install it with: brew install openapi-generator"
    exit 1
fi

echo "📋 Using OpenAPI spec: $API_SPEC"

# Remove existing generated client
if [ -d "$GENERATED_DIR/LingibleAPI" ]; then
    echo "🗑️  Removing existing generated client..."
    rm -rf "$GENERATED_DIR/LingibleAPI"
fi

# Create generated directory if it doesn't exist
mkdir -p "$GENERATED_DIR"

# Generate the iOS client SDK
echo "🔧 Generating iOS client SDK..."
cd "$GENERATED_DIR"

openapi-generator generate \
    -i "$API_SPEC" \
    -g swift5 \
    -o LingibleAPI \
    --package-name LingibleAPI \
    --additional-properties=projectName=LingibleAPI,packageVersion=1.0.0

# Verify the Package.swift was created
if [ ! -f "LingibleAPI/Package.swift" ]; then
    echo "❌ Error: Package.swift was not generated"
    exit 1
fi

echo "✅ iOS Client SDK generated successfully!"
echo "📍 Location: $GENERATED_DIR/LingibleAPI"
echo ""
echo "📝 Next steps:"
echo "1. Open Xcode project: $SCRIPT_DIR/Lingible/Lingible.xcodeproj"
echo "2. The project should automatically resolve the local package at ../generated/LingibleAPI"
echo "3. If you see package resolution issues, try:"
echo "   - Product → Clean Build Folder"
echo "   - File → Packages → Reset Package Caches"
echo "   - File → Packages → Resolve Package Versions"
echo ""
echo "🔍 Package structure:"
echo "   - Package.swift: Swift Package Manager configuration"
echo "   - LingibleAPI/Classes/: Generated Swift code"
echo "   - LingibleAPI/Classes/OpenAPIs/APIs/: API client classes"
echo "   - LingibleAPI/Classes/OpenAPIs/Models/: Data models"

