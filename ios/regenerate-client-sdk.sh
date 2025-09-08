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

# Apply post-generation patches
echo "🔧 Applying post-generation patches..."

# Fix OpenISO8601DateFormatter to handle microseconds
DATE_FORMATTER_FILE="LingibleAPI/LingibleAPI/Classes/OpenAPIs/OpenISO8601DateFormatter.swift"
if [ -f "$DATE_FORMATTER_FILE" ]; then
    echo "📅 Patching OpenISO8601DateFormatter to handle microseconds..."

    # Add microseconds formatter
    sed -i '' '/static let withoutTime: DateFormatter = {/,/}()/{
        /}()/a\
\
    static let withMicroseconds: DateFormatter = {\
        let formatter = DateFormatter()\
        formatter.calendar = Calendar(identifier: .iso8601)\
        formatter.locale = Locale(identifier: "en_US_POSIX")\
        formatter.timeZone = TimeZone(secondsFromGMT: 0)\
        formatter.dateFormat = "yyyy-MM-dd'\''T'\''HH:mm:ss.SSSSSSZZZZZ"\
        return formatter\
    }()
    }' "$DATE_FORMATTER_FILE"

    # Update the date parsing method to try microseconds first
    python3 -c "
import re

# Read the file
with open('$DATE_FORMATTER_FILE', 'r') as f:
    content = f.read()

# Replace the date parsing method
old_method = '''    override public func date(from string: String) -> Date? {
        if let result = super.date(from: string) {
            return result
        } else if let result = OpenISO8601DateFormatter.withoutSeconds.date(from: string) {
            return result
        }

        return OpenISO8601DateFormatter.withoutTime.date(from: string)
    }'''

new_method = '''    override public func date(from string: String) -> Date? {
        // Try microseconds first (6 digits)
        if let result = OpenISO8601DateFormatter.withMicroseconds.date(from: string) {
            return result
        }
        // Try standard format (3 digits milliseconds)
        if let result = super.date(from: string) {
            return result
        }
        // Try without seconds
        if let result = OpenISO8601DateFormatter.withoutSeconds.date(from: string) {
            return result
        }
        // Try date only
        return OpenISO8601DateFormatter.withoutTime.date(from: string)
    }'''

# Replace the method
content = content.replace(old_method, new_method)

# Write back to file
with open('$DATE_FORMATTER_FILE', 'w') as f:
    f.write(content)
"

    echo "✅ OpenISO8601DateFormatter patched successfully"
else
    echo "⚠️  Warning: OpenISO8601DateFormatter.swift not found, skipping patch"
fi

echo "✅ iOS Client SDK generated and patched successfully!"
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
