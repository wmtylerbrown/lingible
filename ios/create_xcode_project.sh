#!/bin/bash

# Script to create Lingible iOS app Xcode project with proper structure
# Run this script from the ios directory

PROJECT_NAME="Lingible"
BUNDLE_ID="com.lingible.lingible"
TEAM_ID=""  # Add your Apple Developer Team ID here
PROJECT_DIR="/Users/tyler/mobile-app-aws-backend/ios"

echo "🚀 Creating Lingible iOS app with clean architecture..."

# Create project directory structure
mkdir -p "$PROJECT_DIR/$PROJECT_NAME"
cd "$PROJECT_DIR"

# Create the Xcode project directory structure manually
mkdir -p "$PROJECT_NAME/$PROJECT_NAME"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME.xcodeproj"

# Create App structure
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/App"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Core/Networking"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Core/Authentication"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Core/Storage"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Core/Design"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Features/Authentication"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Features/Translation"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Features/Profile"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Features/Subscription"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Models"
mkdir -p "$PROJECT_NAME/$PROJECT_NAME/Resources"

# Copy assets from shared directory
echo "📱 Copying assets..."
cp -r "../shared/assets/ios-assets" "$PROJECT_NAME/$PROJECT_NAME/Resources/Assets.xcassets"

# Create Package.swift for SPM dependencies
cat > "$PROJECT_NAME/Package.swift" << 'EOF'
// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "Lingible",
    platforms: [
        .iOS(.v15)
    ],
    products: [
        .library(
            name: "Lingible",
            targets: ["Lingible"]
        ),
    ],
    dependencies: [
        // AWS Amplify for Cognito
        .package(url: "https://github.com/aws-amplify/amplify-swift.git", from: "2.0.0"),
        // Generated API Client (local dependency)
        .package(path: "../generated/LingibleAPI")
    ],
    targets: [
        .target(
            name: "Lingible",
            dependencies: [
                .product(name: "Amplify", package: "amplify-swift"),
                .product(name: "AWSCognitoAuthPlugin", package: "amplify-swift"),
                .product(name: "LingibleAPI", package: "LingibleAPI")
            ]
        ),
        .testTarget(
            name: "LingibleTests",
            dependencies: ["Lingible"]
        ),
    ]
)
EOF

echo "✅ Created project structure in $PROJECT_NAME/"
echo "📝 Next steps:"
echo "1. Open Xcode and create a new iOS project at: $PROJECT_DIR/$PROJECT_NAME"
echo "2. Set Bundle ID to: $BUNDLE_ID"
echo "3. Enable Apple Sign In capability"
echo "4. Configure Swift Package Manager dependencies"
echo "5. Add the generated API client as a local package"

ls -la "$PROJECT_NAME"
