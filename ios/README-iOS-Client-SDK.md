# iOS Client SDK Management

This document describes the consistent workflow for managing the iOS client SDK generated from our OpenAPI specification.

## Overview

The iOS client SDK is automatically generated from the OpenAPI specification using `openapi-generator`. It's structured as a Swift Package that can be referenced locally by the Xcode project.

## Directory Structure

```
ios/
├── generated/
│   └── LingibleAPI/           # Generated Swift Package
│       ├── Package.swift      # Swift Package Manager config
│       ├── LingibleAPI/
│       │   └── Classes/
│       │       └── OpenAPIs/
│       │           ├── APIs/          # API client classes
│       │           └── Models/        # Data models
│       └── README.md
├── Lingible/
│   └── Lingible.xcodeproj     # Xcode project
└── regenerate-client-sdk.sh   # Regeneration script
```

## Workflow

### 1. Regenerating the Client SDK

When the OpenAPI specification changes, regenerate the iOS client:

```bash
cd ios
./regenerate-client-sdk.sh
```

This script:
- Removes the existing generated client
- Generates a new client from the OpenAPI spec
- Ensures consistent package structure
- Provides next steps for Xcode integration

### 2. Xcode Integration

The Xcode project is configured to reference the local Swift package:

- **Package Reference**: `../generated/LingibleAPI`
- **Product**: `LingibleAPI`
- **Type**: Local Swift Package

### 3. Troubleshooting Package Issues

If you encounter "Missing package product 'LingibleAPI'" errors:

1. **Clean Build Folder**: `Product → Clean Build Folder`
2. **Reset Package Caches**: `File → Packages → Reset Package Caches`
3. **Resolve Package Versions**: `File → Packages → Resolve Package Versions`
4. **Verify Package Path**: Ensure `../generated/LingibleAPI` exists and contains `Package.swift`

### 4. API Usage

The generated client provides:

```swift
import LingibleAPI

// API clients
TranslationAPI.translatePost(...)
UserAPI.userUpgradePost(...)
TrendingAPI.trendingGet(...)

// Data models
TranslationRequest(...)
UpgradeRequest(...)
TrendingListResponse(...)
```

## Important Notes

### Package Structure Consistency

The `openapi-generator` creates a specific directory structure:
- `LingibleAPI/Classes/` contains the actual Swift code
- `Package.swift` references this path in the target configuration
- The package name is always `LingibleAPI`

### Version Management

- The generated package version is set to `1.0.0`
- Each regeneration creates a fresh package (no versioning conflicts)
- The Xcode project references the local package, not a remote one

### Dependencies

The generated package includes:
- `AnyCodable` for flexible JSON handling
- Standard Swift libraries

## Common Issues and Solutions

### Issue: "Missing package product 'LingibleAPI'"

**Cause**: Xcode package resolution cache issues or incorrect package path

**Solution**:
1. Verify the package exists at `../generated/LingibleAPI`
2. Check that `Package.swift` exists and is valid
3. Reset Xcode package caches
4. Clean and rebuild the project

### Issue: Build errors after regeneration

**Cause**: API changes in the generated client

**Solution**:
1. Update import statements if needed
2. Update API calls to match new signatures
3. Update model usage for changed properties

### Issue: Package not found during build

**Cause**: Incorrect relative path in Xcode project

**Solution**:
1. Verify the package reference path is `../generated/LingibleAPI`
2. Ensure the path is relative to the Xcode project location
3. Re-add the package if the path is incorrect

## Best Practices

1. **Always use the regeneration script** instead of manual generation
2. **Test the build** after each regeneration
3. **Update API usage** immediately after regeneration if needed
4. **Commit the generated code** to version control for team consistency
5. **Document any custom modifications** to the generated code

## Integration with API Spec Changes

When the OpenAPI specification is updated:

1. Update the spec file: `shared/api/openapi/lingible-api.yaml`
2. Regenerate the iOS client: `cd ios && ./regenerate-client-sdk.sh`
3. Update any affected Swift code in the app
4. Test the build and functionality
5. Commit all changes together

This ensures the iOS client stays in sync with the backend API implementation.
