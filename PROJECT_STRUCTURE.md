# Lingible Project Structure

## 🏗️ Complete Project Organization

This document outlines the recommended structure for the Lingible project, designed to scale from the current backend to include iOS and Android apps while maintaining clean separation of concerns.

## 📁 Root Structure

```
mobile-app-aws-backend/
├── backend/                    # Backend services (Python + TypeScript)
├── ios/                       # iOS app (Swift/Objective-C)
├── android/                   # Android app (Kotlin/Java)
├── shared/                    # Shared resources and utilities
├── memory-bank/              # Project context and task tracking
├── docs/                     # Public documentation
├── scripts/                  # Project-wide scripts
├── .gitignore
├── README.md
└── PROJECT_STRUCTURE.md
```

## 🔧 Backend Structure (Current)

```
backend/
├── lambda/                    # Python Lambda functions
│   ├── src/                  # Lambda function source code
│   │   ├── handlers/         # API Gateway Lambda handlers
│   │   │   ├── translate_api/
│   │   │   ├── user_profile_api/
│   │   │   ├── user_usage_api/
│   │   │   ├── translation_history_api/
│   │   │   ├── user_upgrade_api/
│   │   │   ├── health_api/
│   │   │   ├── authorizer/
│   │   │   ├── apple_webhook/
│   │   │   ├── cognito_post_confirmation/
│   │   │   ├── cognito_pre_authentication/
│   │   │   ├── cognito_pre_user_deletion/
│   │   │   └── user_data_cleanup/
│   │   ├── models/           # Pydantic data models
│   │   │   ├── base.py
│   │   │   ├── users.py
│   │   │   ├── translations.py
│   │   │   ├── subscriptions.py
│   │   │   ├── events.py
│   │   │   └── aws.py
│   │   ├── services/         # Business logic layer
│   │   │   ├── translation_service.py
│   │   │   ├── user_service.py
│   │   │   ├── subscription_service.py
│   │   │   └── receipt_validation_service.py
│   │   ├── repositories/     # Data access layer
│   │   │   ├── user_repository.py
│   │   │   ├── translation_repository.py
│   │   │   └── subscription_repository.py
│   │   └── utils/            # Shared utilities
│   │       ├── aws_services.py
│   │       ├── exceptions.py
│   │       ├── response.py
│   │       ├── decorators.py
│   │       ├── envelopes.py
│   │       ├── logging.py
│   │       ├── tracing.py
│   │       └── config.py
│   ├── tests/                # Test suite
│   │   ├── conftest.py
│   │   ├── test_models.py
│   │   ├── test_services.py
│   │   ├── test_repositories.py
│   │   ├── test_handlers.py
│   │   ├── test_utils.py
│   │   └── README.md
│   ├── requirements.txt      # Python dependencies
│   ├── pytest.ini          # Pytest configuration
│   ├── mypy.ini            # MyPy type checking configuration
│   ├── run_tests.py        # Test execution script
│   ├── cleanup.sh          # Python cleanup script
│   ├── test_receipt_validation.py
│   └── README.md           # Lambda development guide
├── infrastructure/           # AWS CDK infrastructure
│   ├── app.ts              # CDK app entry point
│   ├── constructs/         # CDK constructs
│   │   ├── backend_stack.ts
│   │   └── hosted_zones_stack.ts
│   ├── stacks/             # CDK stacks
│   │   └── lingible_stack.ts
│   ├── scripts/            # Infrastructure scripts
│   │   ├── build-lambda-packages.js
│   │   ├── get-dns-info.js
│   │   └── manage-apple-secret.js
│   ├── test/               # Infrastructure tests
│   │   ├── backend-stack.test.ts
│   │   ├── hosted-zones-stack.test.ts
│   │   └── setup.ts
│   ├── utils/              # Utility functions and config loaders
│   │   └── config-loader.ts # Shared config loader for CDK
│   ├── package.json        # Node.js dependencies
│   ├── package-lock.json
│   ├── tsconfig.json       # TypeScript configuration
│   ├── cdk.json           # CDK configuration
│   ├── jest.config.js     # Jest configuration
│   └── README.md          # Infrastructure guide
└── docs/                   # Backend documentation
    ├── api-completeness-analysis.md
    ├── api-gateway-only-architecture.md
    ├── apple-credentials-security.md
    ├── authorization-guide.md
    ├── aws_services_efficiency.md
    ├── cognito-triggers.md
    ├── logging-strategy.md
    ├── receipt-validation-guide.md
    ├── translation-storage-cost-optimization.md
    └── user-lifecycle-analysis.md
```

## 📱 iOS App Structure (Future)

```
ios/
├── Lingible/                # Main iOS app
│   ├── Lingible.xcodeproj/  # Xcode project
│   ├── Lingible/            # App source code
│   │   ├── App/            # App entry point
│   │   │   ├── LingibleApp.swift
│   │   │   └── ContentView.swift
│   │   ├── Features/       # Feature modules
│   │   │   ├── Translation/
│   │   │   │   ├── Views/
│   │   │   │   ├── ViewModels/
│   │   │   │   ├── Models/
│   │   │   │   └── Services/
│   │   │   ├── Profile/
│   │   │   │   ├── Views/
│   │   │   │   ├── ViewModels/
│   │   │   │   └── Models/
│   │   │   ├── Authentication/
│   │   │   │   ├── Views/
│   │   │   │   ├── ViewModels/
│   │   │   │   └── Services/
│   │   │   └── Settings/
│   │   │       ├── Views/
│   │   │       └── ViewModels/
│   │   ├── Core/           # Core app components
│   │   │   ├── Networking/
│   │   │   │   ├── APIClient.swift
│   │   │   │   ├── Endpoints.swift
│   │   │   │   └── Models/
│   │   │   ├── Authentication/
│   │   │   │   ├── CognitoService.swift
│   │   │   │   └── AppleSignIn.swift
│   │   │   ├── Storage/
│   │   │   │   ├── UserDefaults+Extensions.swift
│   │   │   │   └── KeychainService.swift
│   │   │   └── Utils/
│   │   │       ├── Extensions/
│   │   │       ├── Constants.swift
│   │   │       └── Helpers.swift
│   │   ├── Resources/      # App resources
│   │   │   ├── Assets.xcassets/
│   │   │   ├── Localizable.strings
│   │   │   └── Info.plist
│   │   └── Tests/          # Unit tests
│   │       ├── TranslationTests/
│   │       ├── AuthenticationTests/
│   │       └── NetworkingTests/
│   ├── Podfile             # CocoaPods dependencies
│   ├── Podfile.lock
│   ├── .swiftlint.yml      # SwiftLint configuration
│   ├── .gitignore
│   └── README.md           # iOS development guide
└── LingibleTests/          # Integration tests
    ├── UITests/
    └── PerformanceTests/
```

## 🤖 Android App Structure (Future)

```
android/
├── app/                     # Main Android app module
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/lingible/lingible/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   ├── MainApplication.kt
│   │   │   │   ├── ui/           # UI components
│   │   │   │   │   ├── translation/
│   │   │   │   │   ├── profile/
│   │   │   │   │   ├── auth/
│   │   │   │   │   └── settings/
│   │   │   │   ├── data/         # Data layer
│   │   │   │   │   ├── api/
│   │   │   │   │   ├── models/
│   │   │   │   │   ├── repository/
│   │   │   │   │   └── local/
│   │   │   │   ├── domain/       # Domain layer
│   │   │   │   │   ├── models/
│   │   │   │   │   ├── repository/
│   │   │   │   │   └── usecases/
│   │   │   │   └── utils/
│   │   │   ├── res/              # Resources
│   │   │   │   ├── layout/
│   │   │   │   ├── values/
│   │   │   │   ├── drawable/
│   │   │   │   └── mipmap/
│   │   │   └── AndroidManifest.xml
│   │   ├── test/                 # Unit tests
│   │   └── androidTest/          # Instrumented tests
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── buildSrc/                     # Build configuration
├── gradle/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── .gitignore
└── README.md                     # Android development guide
```

## 🔗 Shared Resources Structure

```
shared/
├── api/                        # API definitions and documentation
│   ├── openapi/               # OpenAPI/Swagger specifications
│   │   ├── lingible-api.yaml
│   │   └── lingible-api.json
│   ├── types/                 # Shared type definitions
│   │   ├── typescript/        # TypeScript types
│   │   │   ├── api.ts
│   │   │   ├── models.ts
│   │   │   └── responses.ts
│   │   ├── swift/             # Swift types
│   │   │   ├── APIModels.swift
│   │   │   └── Responses.swift
│   │   └── kotlin/            # Kotlin types
│   │       ├── ApiModels.kt
│   │       └── Responses.kt
│   └── docs/                  # API documentation
│       ├── endpoints.md
│       ├── authentication.md
│       └── examples.md
├── config/                     # Shared configuration
│   ├── environments/
│   │   ├── dev.json
│   │   ├── staging.json
│   │   └── prod.json
│   ├── feature-flags/
│   │   └── flags.json
│   └── constants/
│       ├── app-constants.json
│       └── api-constants.json
├── assets/                     # Shared assets
│   ├── images/
│   │   ├── logos/
│   │   ├── icons/
│   │   └── illustrations/
│   ├── fonts/
│   └── branding/
│       ├── style-guide.md
│       └── color-palette.json
└── utils/                      # Shared utilities
    ├── scripts/
    │   ├── generate-types.sh
    │   ├── validate-api.sh
    │   └── deploy-docs.sh
    └── templates/
        ├── api-client/
        └── documentation/
```

## 📚 Documentation Structure

```
docs/
├── getting-started/           # Onboarding documentation
│   ├── setup.md
│   ├── development.md
│   └── deployment.md
├── api/                       # API documentation
│   ├── reference/
│   ├── guides/
│   └── examples/
├── architecture/              # System architecture
│   ├── overview.md
│   ├── backend.md
│   ├── mobile.md
│   └── infrastructure.md
├── development/               # Development guides
│   ├── contributing.md
│   ├── testing.md
│   ├── code-style.md
│   └── troubleshooting.md
└── deployment/                # Deployment guides
    ├── backend.md
    ├── ios.md
    ├── android.md
    └── infrastructure.md
```

## 🛠️ Scripts Structure

```
scripts/
├── setup/                     # Setup scripts
│   ├── setup-dev-environment.sh
│   ├── setup-ios-environment.sh
│   └── setup-android-environment.sh
├── deployment/                # Deployment scripts
│   ├── deploy-backend.sh
│   ├── deploy-ios.sh
│   └── deploy-android.sh
├── testing/                   # Testing scripts
│   ├── run-all-tests.sh
│   ├── generate-test-reports.sh
│   └── validate-api.sh
├── maintenance/               # Maintenance scripts
│   ├── cleanup-workspace.sh
│   ├── update-dependencies.sh
│   └── backup-database.sh
└── ci/                        # CI/CD scripts
    ├── build-and-test.sh
    ├── deploy-staging.sh
    └── deploy-production.sh
```

## 🧠 Memory Bank Structure

```
memory-bank/
├── activeContext.md           # Current project context
├── tasks.md                   # Active task tracking
├── progress.md                # Project progress
├── projectbrief.md            # Project overview
├── productContext.md          # Product requirements
├── systemPatterns.md          # System design patterns
├── techContext.md             # Technical context
├── style-guide.md             # Code style guidelines
├── tdd-rule.md               # TDD workflow rules
├── archive/                   # Completed task archives
│   ├── archive-[task-id].md
│   └── ...
├── creative/                  # Creative phase documentation
│   ├── creative-[feature_name].md
│   └── ...
└── reflection/                # Task reflections
    ├── reflection-[task_id].md
    └── ...
```

## 🎯 Key Principles

### **1. Separation of Concerns**
- **Backend**: Python Lambda + TypeScript CDK
- **Mobile**: Native iOS (Swift) + Native Android (Kotlin)
- **Shared**: Common types, configs, and utilities

### **2. Language-Specific Organization**
- Each platform has its own directory with appropriate structure
- Configuration files co-located with relevant code
- Platform-specific tools and scripts

### **3. Shared Resources**
- Common API definitions and types
- Shared configuration and constants
- Reusable assets and utilities

### **4. Scalability**
- Easy to add new platforms (web, desktop, etc.)
- Modular feature organization
- Clear dependency management

### **5. Developer Experience**
- Intuitive navigation
- Clear documentation
- Consistent patterns across platforms

## 🚀 Migration Path

### **Phase 1: Current State** ✅
- Backend reorganization complete
- Infrastructure properly organized
- Documentation updated

### **Phase 2: Shared Resources** ✅
- ✅ Create `shared/` directory
- ✅ Extract common types and configurations
- ✅ Set up API documentation

### **Phase 3: iOS App** (Future)
- Create `ios/` directory
- Set up Xcode project
- Implement core features

### **Phase 4: Android App** (Future)
- Create `android/` directory
- Set up Android Studio project
- Implement core features

### **Phase 5: Integration** (Future)
- Cross-platform testing
- Shared CI/CD pipeline
- Unified deployment process

This structure provides a solid foundation for scaling the Lingible project from a backend-only application to a full-stack mobile platform while maintaining clean organization and developer productivity.
