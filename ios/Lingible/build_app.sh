#!/bin/bash

# iOS App Build Script for Lingible
# This script builds the app for development, production, or both environments
# with the correct amplify_outputs.json files
#
# Usage:
#   ./build_app.sh [dev|prod|both]
#   - dev:  Build only development (Debug configuration)
#   - prod: Build only production (Release configuration)
#   - both: Build both environments (default if no parameter)

set -e  # Exit on any error

# Parse command line arguments
BUILD_TARGET=${1:-both}  # Default to 'both' if no parameter provided

# Validate parameter
if [[ "$BUILD_TARGET" != "dev" && "$BUILD_TARGET" != "prod" && "$BUILD_TARGET" != "both" ]]; then
    echo "❌ Invalid parameter: $BUILD_TARGET"
    echo "Usage: $0 [dev|prod|both]"
    echo "  dev:  Build only development (Debug configuration)"
    echo "  prod: Build only production (Release configuration)"
    echo "  both: Build both environments (default)"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to build the app
build_app() {
    local environment=$1
    local configuration=$2
    local amplify_file=$3
    local bundle_id=$4
    local app_name=$5

    print_status "Building $environment app ($configuration configuration)..."

    # Copy the correct amplify_outputs file (force overwrite)
    print_status "Setting up amplify_outputs.json for $environment..."
    rm -f "Lingible/amplify_outputs.json"
    cp "$amplify_file" "Lingible/amplify_outputs.json"

    # Build the app
    print_status "Building $app_name with bundle ID: $bundle_id"
    xcodebuild -project Lingible.xcodeproj \
               -scheme Lingible \
               -configuration "$configuration" \
               -destination 'platform=iOS Simulator,name=iPhone 16,OS=latest' \
               -derivedDataPath "./DerivedData" \
               build

    if [ $? -eq 0 ]; then
        print_success "$environment build completed successfully!"

        # Show build output location
        local build_path="./DerivedData/Build/Products/$configuration-iphonesimulator/$app_name.app"
        print_status "Build output: $build_path"

        # Get build size
        if [ -d "$build_path" ]; then
            local size=$(du -sh "$build_path" | cut -f1)
            print_status "Build size: $size"
        fi
    else
        print_error "$environment build failed!"
        exit 1
    fi
}

# Main execution
echo "🚀 Starting Lingible iOS App Build Process"
echo "=========================================="
echo "🎯 Build target: $BUILD_TARGET"
echo ""

# Check if we're in the right directory
if [ ! -f "Lingible.xcodeproj/project.pbxproj" ]; then
    print_error "Please run this script from the ios/Lingible directory"
    exit 1
fi

# Check if amplify_outputs files exist
if [ ! -f "Lingible/amplify_outputs-dev.json" ]; then
    print_error "amplify_outputs-dev.json not found!"
    exit 1
fi

if [ ! -f "Lingible/amplify_outputs-prod.json" ]; then
    print_error "amplify_outputs-prod.json not found!"
    exit 1
fi

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf ./DerivedData
xcodebuild clean -project Lingible.xcodeproj -scheme Lingible

# Track what was built for summary
BUILT_ENVIRONMENTS=()

# Build based on target
if [[ "$BUILD_TARGET" == "dev" || "$BUILD_TARGET" == "both" ]]; then
    echo ""
    echo "📱 Building Development App (Debug)"
    echo "==================================="
    build_app "Development" "Debug" "Lingible/amplify_outputs-dev.json" "com.lingible.lingible.dev" "Lingible Dev"
    BUILT_ENVIRONMENTS+=("Development")
fi

if [[ "$BUILD_TARGET" == "prod" || "$BUILD_TARGET" == "both" ]]; then
    echo ""
    echo "📱 Building Production App (Release)"
    echo "==================================="
    build_app "Production" "Release" "Lingible/amplify_outputs-prod.json" "com.lingible.lingible" "Lingible"
    BUILT_ENVIRONMENTS+=("Production")
fi

echo ""
print_success "Build(s) completed successfully!"

# Restore appropriate configuration based on what was built
if [[ "$BUILD_TARGET" == "dev" ]]; then
    # Keep dev config in place
    print_status "Keeping development configuration active..."
    print_success "Development configuration is ready for testing"
else
    print_status "Restoring development configuration for testing..."
    rm -f "Lingible/amplify_outputs.json"
    cp "Lingible/amplify_outputs-dev.json" "Lingible/amplify_outputs.json"
    print_success "Development configuration restored"
fi

echo ""
echo "📋 Build Summary:"
echo "=================="
for env in "${BUILT_ENVIRONMENTS[@]}"; do
    if [[ "$env" == "Development" ]]; then
        echo "• Development build: Debug configuration with dev amplify_outputs"
    else
        echo "• Production build: Release configuration with prod amplify_outputs"
    fi
done
echo "• All builds are iPhone-only (no iPad support)"
echo "• Build outputs are in ./DerivedData/Build/Products/"

if [[ "$BUILD_TARGET" == "both" ]]; then
    echo "• amplify_outputs.json restored to development configuration"
    echo ""
    echo "🎯 Next steps:"
    echo "• Test the development build in the simulator (ready to go!)"
    echo "• Archive the production build for App Store submission"
    echo "• Verify both builds use the correct API endpoints"
elif [[ "$BUILD_TARGET" == "dev" ]]; then
    echo "• amplify_outputs.json configured for development"
    echo ""
    echo "🎯 Next steps:"
    echo "• Test the development build in the simulator (ready to go!)"
    echo "• Use Xcode build button (⌘+B) for quick rebuilds"
elif [[ "$BUILD_TARGET" == "prod" ]]; then
    echo "• amplify_outputs.json configured for production"
    echo ""
    echo "🎯 Next steps:"
    echo "• Test the production build in the simulator"
    echo "• Archive for App Store submission when ready"
fi
