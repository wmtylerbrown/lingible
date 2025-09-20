#!/bin/bash

# iOS App Build Script for Lingible
# This script builds the app for development, production, or both environments
# with the correct amplify_outputs.json files
#
# Usage:
#   ./build_app.sh [dev|prod|both|archive] [--clean]
#   - dev:     Build only development (Debug configuration)
#   - prod:    Build only production (Release configuration)
#   - both:    Build both environments (default if no parameter)
#   - archive: Create production archive for App Store submission
#   - --clean: Optional clean step before building (slower but ensures fresh build)
#
# Examples:
#   ./build_app.sh dev          # Quick dev build (no clean)
#   ./build_app.sh dev --clean  # Clean dev build (slower)
#   ./build_app.sh --clean dev  # Same as above
#   ./build_app.sh both         # Build both dev and prod (no clean)
#   ./build_app.sh archive      # Create archive (always cleans)

set -e  # Exit on any error

# Parse command line arguments
BUILD_TARGET=${1:-both}  # Default to 'both' if no parameter provided
CLEAN_BUILD=false

# Check for clean flag
if [[ "$1" == "--clean" ]]; then
    CLEAN_BUILD=true
    BUILD_TARGET=${2:-both}  # Get the actual build target from second parameter
elif [[ "$2" == "--clean" ]]; then
    CLEAN_BUILD=true
fi

# Validate parameter
if [[ "$BUILD_TARGET" != "dev" && "$BUILD_TARGET" != "prod" && "$BUILD_TARGET" != "both" && "$BUILD_TARGET" != "archive" ]]; then
    echo "❌ Invalid parameter: $BUILD_TARGET"
    echo "Usage: $0 [dev|prod|both|archive] [--clean]"
    echo "  dev:     Build only development (Debug configuration)"
    echo "  prod:    Build only production (Release configuration)"
    echo "  both:    Build both environments (default)"
    echo "  archive: Create production archive for App Store submission"
    echo "  --clean: Optional clean step before building (slower but ensures fresh build)"
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

# Function to clean build artifacts
clean_build() {
    print_status "Cleaning previous builds..."
    rm -rf ./DerivedData
    xcodebuild clean -project Lingible.xcodeproj -scheme Lingible
    print_success "Clean completed"
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
               -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.6' \
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

# Function to create archive for App Store submission
create_archive() {
    print_status "Creating production archive for App Store submission..."

    # Clean previous builds for archive (ensures clean App Store submission)
    print_status "Cleaning previous builds for archive..."
    rm -rf ./DerivedData
    xcodebuild clean -project Lingible.xcodeproj -scheme Lingible

    # Copy the production amplify_outputs file
    print_status "Setting up amplify_outputs.json for production..."
    rm -f "Lingible/amplify_outputs.json"
    cp "Lingible/amplify_outputs-prod.json" "Lingible/amplify_outputs.json"

    # Create archive
    local archive_name="Lingible-Production-$(date +%Y%m%d-%H%M%S).xcarchive"
    print_status "Creating archive: $archive_name"

    xcodebuild -project Lingible.xcodeproj \
               -scheme Lingible \
               -configuration Release \
               -destination generic/platform=iOS \
               -archivePath "./$archive_name" \
               archive

    if [ $? -eq 0 ]; then
        print_success "Archive created successfully!"

        # Move archive to Xcode Archives directory
        local archives_dir="$HOME/Library/Developer/Xcode/Archives/$(date +%Y-%m-%d)"
        mkdir -p "$archives_dir"
        mv "./$archive_name" "$archives_dir/"

        print_success "Archive moved to: $archives_dir/$archive_name"

        # Clean up AdMob dSYM files to prevent upload issues
        print_status "Cleaning up AdMob dSYM files..."
        find "$archives_dir/$archive_name" -name "*GoogleMobileAds*" -type d -exec rm -rf {} + 2>/dev/null || true
        find "$archives_dir/$archive_name" -name "*UserMessagingPlatform*" -type d -exec rm -rf {} + 2>/dev/null || true

        print_success "AdMob dSYM cleanup completed"

        # Show archive info
        local archive_size=$(du -sh "$archives_dir/$archive_name" | cut -f1)
        print_status "Archive size: $archive_size"

        # Verify production configuration
        if grep -q "auth.lingible.com" "$archives_dir/$archive_name/Products/Applications/Lingible.app/amplify_outputs.json"; then
            print_success "✅ Production configuration verified in archive"
        else
            print_error "❌ Archive does not contain production configuration!"
            exit 1
        fi

        echo ""
        print_success "🎉 Archive ready for App Store submission!"
        echo "📱 Archive location: $archives_dir/$archive_name"
        echo "🔧 Next steps:"
        echo "   1. Open Xcode Organizer (Window → Organizer)"
        echo "   2. Select the 'Archives' tab"
        echo "   3. Find your archive and click 'Distribute App'"
        echo "   4. Choose 'App Store Connect' for submission"

    else
        print_error "Archive creation failed!"
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

# Optional clean step
if [[ "$CLEAN_BUILD" == "true" ]]; then
    echo ""
    echo "🧹 Optional Clean Build"
    echo "======================"
    clean_build
fi

# Track what was built for summary
BUILT_ENVIRONMENTS=()

# Build based on target
if [[ "$BUILD_TARGET" == "archive" ]]; then
    echo ""
    echo "📦 Creating Production Archive"
    echo "============================="
    create_archive
    BUILT_ENVIRONMENTS+=("Archive")
elif [[ "$BUILD_TARGET" == "dev" || "$BUILD_TARGET" == "both" ]]; then
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

print_status "Restoring development configuration for testing..."
rm -f "Lingible/amplify_outputs.json"
cp "Lingible/amplify_outputs-dev.json" "Lingible/amplify_outputs.json"
print_success "Development configuration restored"

echo ""
echo "📋 Build Summary:"
echo "=================="
if [[ "$CLEAN_BUILD" == "true" ]]; then
    echo "• Clean build: Previous artifacts removed before building"
fi
for env in "${BUILT_ENVIRONMENTS[@]}"; do
    if [[ "$env" == "Development" ]]; then
        echo "• Development build: Debug configuration with dev amplify_outputs"
    elif [[ "$env" == "Production" ]]; then
        echo "• Production build: Release configuration with prod amplify_outputs"
    elif [[ "$env" == "Archive" ]]; then
        echo "• Production archive: Release configuration with prod amplify_outputs"
    fi
done
echo "• All builds are iPhone-only (no iPad support)"
if [[ "$BUILD_TARGET" != "archive" ]]; then
    echo "• Build outputs are in ./DerivedData/Build/Products/"
fi

if [[ "$BUILD_TARGET" == "archive" ]]; then
    echo "• amplify_outputs.json configured for production"
    echo ""
    echo "🎯 Next steps:"
    echo "• Open Xcode Organizer (Window → Organizer)"
    echo "• Select the 'Archives' tab"
    echo "• Find your archive and click 'Distribute App'"
    echo "• Choose 'App Store Connect' for submission"
elif [[ "$BUILD_TARGET" == "both" ]]; then
    echo "• amplify_outputs.json restored to development configuration"
    echo ""
    echo "🎯 Next steps:"
    echo "• Test the development build in the simulator (ready to go!)"
    echo "• Run './build_app.sh archive' to create App Store archive"
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
    echo "• Run './build_app.sh archive' to create App Store archive"
fi
