# 🚀 Lingible iOS App Setup Guide

This guide will walk you through setting up the Lingible iOS app from the generated structure.

## ✅ **What We've Created**

1. **✅ Generated Swift API Client** from OpenAPI spec
2. **✅ Clean Architecture Foundation** with protocols and dependency injection
3. **✅ Complete App Structure** with all necessary files
4. **✅ Theme System** based on the original app design
5. **✅ Authentication Flow** with Apple Sign In and Cognito
6. **✅ Translation Feature** with beautiful card-based UI
7. **✅ Assets** extracted from the original app

## 📋 **Next Steps in Xcode**

### Step 1: Prepare Directory and Create Xcode Project

**Important**: We need to temporarily rename our source folder to avoid conflicts with the Xcode project name.

1. **Rename source folder**:
```bash
cd /Users/tyler/mobile-app-aws-backend/ios
mv Lingible LingibleSource
```

2. **Create Xcode project**:
   - Open Xcode
   - Create **New Project** → **iOS** → **App**
   - **Save location**: Navigate to `/Users/tyler/mobile-app-aws-backend/ios/`
   - Set:
     - **Product Name**: `Lingible` (or any name you prefer)
     - **Bundle Identifier**: Xcode will auto-generate this, we'll fix it in the next step
     - **Language**: Swift
     - **Interface**: SwiftUI
     - **Use Core Data**: No
   - Click **Create**

### Step 2: Configure Project Settings
1. **General Tab**:
   - **Bundle Identifier**: Change this to `com.lingible.lingible` (lowercase!)
   - **Deployment Target**: iOS 16.0
   - **Supported Destinations**: iPhone, iPad

2. **Signing & Capabilities**:
   - Select your **Team**
   - Add Capability: **Sign in with Apple**

### Step 3: Add Package Dependencies
1. **File** → **Add Package Dependencies**
2. Add these packages:

   **AWS Amplify Swift**:
   ```
   https://github.com/aws-amplify/amplify-swift.git
   ```
   Select: `Amplify`, `AWSCognitoAuthPlugin`

   **Local API Client**:
   - Click **Add Local**
   - Navigate to: `generated/LingibleAPI` (relative to your project)
   - Select the package

### Step 4: Replace Default Files
1. **Delete** the default `ContentView.swift` that Xcode created
2. **Copy** all our source files:
```bash
# Copy our prepared source files to the Xcode project
cp -r LingibleApp/Lingible/* Lingible/Lingible/
```
3. **In Xcode**: Right-click on your project → **Add Files to "Lingible"**
4. **Select all** the copied `.swift` files and add them to your target
5. **Clean up**: `rm -rf LingibleApp` (optional, but keeps things tidy)

### Step 5: Add Assets
1. **Delete** the default Assets.xcassets that Xcode created
2. **Copy** our assets:
```bash
# Copy our extracted assets
cp -r LingibleApp/Lingible/Resources/Assets.xcassets Lingible/Lingible/
```
3. **In Xcode**: Drag the `Assets.xcassets` folder into your project navigator
4. **Add to target** when prompted

### Step 6: Create Amplify Configuration
Create `amplifyconfiguration.json` in your project root:

```json
{
  "auth": {
    "plugins": {
      "awsCognitoAuthPlugin": {
        "UserAgent": "aws-amplify-cli/0.1.0",
        "Version": "0.1.0",
        "IdentityManager": {
          "Default": {}
        },
        "CredentialsProvider": {
          "CognitoIdentity": {
            "Default": {
              "PoolId": "YOUR_IDENTITY_POOL_ID",
              "Region": "us-east-1"
            }
          }
        },
        "CognitoUserPool": {
          "Default": {
            "PoolId": "YOUR_USER_POOL_ID",
            "AppClientId": "YOUR_APP_CLIENT_ID",
            "Region": "us-east-1"
          }
        },
        "Auth": {
          "Default": {
            "authenticationFlowType": "USER_SRP_AUTH"
          }
        }
      }
    }
  }
}
```

**To get these values**:
- Run: `aws cognito-idp list-user-pools --max-items 10`
- Run: `aws cognito-identity list-identity-pools --max-items 10`
- Or check your CDK outputs after deployment

## 🎨 **App Architecture Overview**

### **Clean Architecture Benefits**:
- ✅ **Testable**: All services use protocols
- ✅ **Maintainable**: Clear separation of concerns
- ✅ **Scalable**: Easy to add new features
- ✅ **Type-Safe**: Generated API client prevents errors

### **Key Improvements Over Old App**:
1. **Single Authentication Service** (not dual services)
2. **Protocol-Based Design** (mockable/testable)
3. **Generated API Client** (always in sync with backend)
4. **Dependency Injection** (no `.shared` singletons)
5. **Smaller Files** (single responsibility principle)

### **File Structure**:
```
App/                 # App entry point & coordination
Core/               # Shared infrastructure
├── Authentication/ # Cognito + Apple Sign In
├── Networking/     # API services
├── Storage/        # Keychain, UserDefaults
└── Design/         # Theme, colors, modifiers
Features/           # Feature modules
├── Authentication/ # Login screens
├── Translation/    # Main translation feature
└── Profile/        # Settings & profile
```

## 🔧 **Build and Test**

### Step 1: Build the Project
1. Press **⌘+B** to build
2. Fix any import issues (should be minimal)

### Step 2: Run on Simulator
1. Select **iPhone 15** simulator
2. Press **⌘+R** to run
3. You should see the splash screen

### Step 3: Test Features
- **Splash Screen**: Beautiful animation with slang terms
- **Authentication**: Apple Sign In button (needs real device for full test)
- **Translation**: Input card and result cards
- **Profile**: Settings and sign out

## 🐛 **Troubleshooting**

### Common Issues:

1. **Build Errors**:
   - Ensure all files are added to target
   - Check Swift Package dependencies are resolved
   - Clean build folder (⌘+Shift+K)

2. **API Client Issues**:
   - Verify local package path is correct
   - Check if LingibleAPI is properly generated

3. **Asset Issues**:
   - Ensure Assets.xcassets is added to target
   - Check asset names match code references

4. **Apple Sign In**:
   - Requires real device for testing
   - Bundle ID must match Apple Developer account
   - Capability must be enabled

## 🚀 **Ready for TestFlight**

Once everything builds and runs:

1. **Archive** the app (⌘+Shift+B)
2. **Upload** to App Store Connect
3. **Configure** TestFlight
4. **Invite** beta testers

## 🎯 **Next Development Steps**

1. **Test** on real device with Apple Sign In
2. **Connect** to deployed backend API
3. **Implement** premium features
4. **Add** push notifications
5. **Polish** UI/UX based on testing

---

The app architecture is **production-ready** and follows iOS best practices. The foundation is solid for scaling to full production! 🎉
