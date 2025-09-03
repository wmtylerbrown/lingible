# Lingible iOS App

A modern, clean architecture iOS app for the Lingible translation service.

## 🏗 Architecture

This app follows **Clean Architecture** principles with:

- **MVVM Pattern**: ViewModels manage business logic
- **Protocol-Based Design**: All services use protocols for testability
- **Dependency Injection**: No singleton `.shared` instances
- **Swift Package Manager**: Modern dependency management
- **Generated API Client**: Type-safe networking from OpenAPI spec

## 📁 Project Structure

```
Lingible/
├── App/                    # App entry point
│   ├── LingibleApp.swift   # Main app file
│   ├── ContentView.swift   # Root view
│   └── AppCoordinator.swift # App state management
├── Core/                   # Shared infrastructure
│   ├── Networking/         # API services
│   ├── Authentication/     # Cognito + Apple Sign In
│   ├── Storage/            # Keychain, UserDefaults
│   └── Design/             # Theme, colors, modifiers
├── Features/               # Feature modules
│   ├── Authentication/     # Login/splash screens
│   ├── Translation/        # Main translation feature
│   ├── Profile/            # User profile & settings
│   └── Subscription/       # Premium upgrades (future)
├── Models/                 # Data models
└── Resources/              # Assets, Info.plist
```

## 🚀 Setup Instructions

### Prerequisites

1. **Xcode 15+** with iOS 15+ deployment target
2. **Apple Developer Account** for Apple Sign In capability
3. **Backend API** running and accessible

### 1. Create Xcode Project

1. Open Xcode and create a new iOS project
2. Choose "iOS" → "App"
3. Set:
   - Product Name: `Lingible`
   - Bundle Identifier: `com.lingible.lingible`
   - Language: Swift
   - Interface: SwiftUI
   - Use Core Data: No

### 2. Configure Project Settings

1. **Deployment Target**: iOS 15.0+
2. **Capabilities**:
   - Enable "Sign in with Apple"
3. **Team**: Select your Apple Developer Team

### 3. Add Package Dependencies

In Xcode, go to **File** → **Add Package Dependencies** and add:

1. **AWS Amplify Swift**:
   ```
   https://github.com/aws-amplify/amplify-swift.git
   ```
   - Select: `Amplify`, `AWSCognitoAuthPlugin`

2. **Local API Package**:
   - Add local package: `../generated/LingibleAPI`

### 4. Copy Source Files

Copy all `.swift` files from this directory structure to your Xcode project:

```bash
# Copy app files
cp -r Lingible/Lingible/* YourXcodeProject/Lingible/

# Copy assets
cp -r Resources/Assets.xcassets YourXcodeProject/Lingible/
```

### 5. Configure Amplify

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

### 6. Configure Apple Sign In

1. In Apple Developer Console:
   - Create App ID with "Sign in with Apple" capability
   - Create Service ID for your app
   - Configure Return URLs in Cognito

2. In AWS Cognito:
   - Add Apple as Identity Provider
   - Configure App Integration

## 🎨 Design System

### Colors

The app uses a custom color system defined in `Core/Design/Colors.swift`:

- **Primary**: Main brand color (blue)
- **Secondary**: Supporting gray colors
- **Background**: Light gray backgrounds
- **Status**: Success, error, warning colors

### Theme Management

The `ThemeManager` supports:
- Light mode
- Dark mode
- System mode (follows device setting)

### Custom Modifiers

- `.scaleAnimation()`: Button press animations
- `.fadeInAnimation(delay:)`: Fade in with delay
- `.cardStyle()`: Consistent card styling

## 🔧 Key Features

### Authentication
- Apple Sign In with Amplify Cognito
- Secure token storage in Keychain
- Automatic token refresh

### Translation
- Clean, card-based UI
- Local caching of translation history
- Real-time usage tracking
- Error handling with user feedback

### Architecture Benefits
- **Testable**: Protocol-based services can be mocked
- **Maintainable**: Clear separation of concerns
- **Scalable**: Easy to add new features
- **Type-Safe**: Generated API client prevents runtime errors

## 🧪 Testing

The app is designed for easy testing:

1. **Unit Tests**: Mock protocols for isolated testing
2. **UI Tests**: SwiftUI preview-friendly components
3. **Integration Tests**: Test API integration with real services

## 🚀 Deployment

### TestFlight
1. Archive the app in Xcode
2. Upload to App Store Connect
3. Configure TestFlight settings
4. Invite beta testers

### App Store
1. Complete App Store Connect metadata
2. Submit for review
3. Release when approved

## 🔍 Troubleshooting

### Common Issues

1. **Apple Sign In not working**:
   - Check Bundle ID matches Apple Developer Console
   - Verify capability is enabled
   - Check Amplify configuration

2. **API calls failing**:
   - Verify backend is running
   - Check API endpoint URLs
   - Confirm authentication tokens

3. **Build errors**:
   - Clean build folder (`⌘+Shift+K`)
   - Reset package caches
   - Check deployment target compatibility

## 📱 Minimum Requirements

- iOS 16.0+
- iPhone and iPad compatible
- Portrait and landscape orientations
- Light and dark mode support

## 🔗 Related Resources

- [Backend API Documentation](../backend/README.md)
- [OpenAPI Specification](../shared/api/openapi/lingible-api.yaml)
- [AWS Amplify Documentation](https://docs.amplify.aws/)
- [Apple Sign In Guide](https://developer.apple.com/sign-in-with-apple/)
