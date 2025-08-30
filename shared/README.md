# Shared Resources - Lingible

This directory contains shared resources and utilities that are used across multiple platforms (backend, iOS, Android) to ensure consistency and reduce duplication for the Lingible teen slang translation app.

## 📁 Structure

```
shared/
├── api/                        # API definitions and documentation
│   ├── openapi/               # OpenAPI/Swagger specifications
│   │   └── lingible-api.yaml  # Complete API specification
│   ├── types/                 # Shared type definitions
│   │   ├── typescript/        # TypeScript types
│   │   │   └── api.ts         # API type definitions
│   │   ├── swift/             # Swift types (future)
│   │   └── kotlin/            # Kotlin types (future)
│   └── docs/                  # API documentation
├── config/                     # Shared configuration
│   ├── app.json               # Application-wide constants and settings
│   └── environments/          # Environment-specific configs
│       ├── dev.json          # Development environment
│       └── prod.json         # Production environment
├── assets/                     # Shared assets
│   ├── images/                # Images and graphics
│   │   ├── logos/            # App logos
│   │   ├── icons/            # App icons
│   │   └── illustrations/    # App illustrations
│   ├── fonts/                # Custom fonts
│   └── branding/             # Branding guidelines
└── utils/                      # Shared utilities
    ├── scripts/               # Utility scripts
    └── templates/             # Code templates
        ├── api-client/        # API client templates
        └── documentation/     # Documentation templates
```

## 🎯 Purpose

### **1. API Consistency**
- **Single Source of Truth**: OpenAPI specification defines all teen slang translation API endpoints
- **Type Safety**: Shared type definitions ensure consistent data structures
- **Documentation**: Centralized API documentation for all platforms

### **2. Configuration Management**
- **Environment-Specific**: Different configs for dev, staging, prod
- **Feature Flags**: Centralized feature management
- **Constants**: Shared application constants

### **3. Asset Management**
- **Brand Consistency**: Centralized logos, icons, and branding
- **Cross-Platform**: Assets optimized for all platforms
- **Version Control**: Track asset changes and updates

### **4. Development Efficiency**
- **Code Generation**: Templates for API clients and documentation
- **Automation**: Scripts for common development tasks
- **Consistency**: Shared patterns across platforms

## 🚀 Usage

### **Backend Development**
```bash
# Reference shared types in backend code
from shared.api.types.typescript.api import TranslationRequest

# Use shared configuration
import shared.config.app as app_config
```

### **iOS Development** (Future)
```swift
// Import shared types
import SharedTypes

// Use shared configuration
let config = SharedConfig.current
```

### **Android Development** (Future)
```kotlin
// Import shared types
import com.lingible.shared.types.*

// Use shared configuration
val config = SharedConfig.current
```

## 📋 API Documentation

### **OpenAPI Specification**
The complete API specification is available at:
- **File**: `api/openapi/lingible-api.yaml`
- **Viewer**: Use Swagger UI or similar tools to view
- **Generation**: Use to generate client SDKs

### **Type Definitions**
- **TypeScript**: `api/types/typescript/api.ts`
- **Swift**: `api/types/swift/` (future)
- **Kotlin**: `api/types/kotlin/` (future)

## ⚙️ Configuration

### **Environment Configs**
- **Development**: `config/environments/dev.json`
- **Production**: `config/environments/prod.json`
- **Staging**: `config/environments/staging.json` (future)

### **App Constants**
- **Core Constants**: `config/constants/app-constants.json`
- **Feature Flags**: `config/feature-flags/` (future)

## 🎨 Assets

### **Branding Guidelines**
- **Style Guide**: `assets/branding/style-guide.md` (future)
- **Color Palette**: `assets/branding/color-palette.json` (future)
- **Typography**: `assets/branding/typography.json` (future)

### **Image Assets**
- **Logos**: `assets/images/logos/`
- **Icons**: `assets/images/icons/`
- **Illustrations**: `assets/images/illustrations/`

## 🛠️ Utilities

### **Scripts**
- **Type Generation**: `utils/scripts/generate-types.sh` (future)
- **API Validation**: `utils/scripts/validate-api.sh` (future)
- **Documentation**: `utils/scripts/deploy-docs.sh` (future)

### **Templates**
- **API Client**: `utils/templates/api-client/`
- **Documentation**: `utils/templates/documentation/`

## 🔄 Maintenance

### **Adding New Endpoints**
1. Update `api/openapi/lingible-api.yaml`
2. Generate/update type definitions
3. Update documentation
4. Test across platforms

### **Adding New Constants**
1. Update `config/constants/app-constants.json`
2. Update environment configs if needed
3. Update platform-specific implementations

### **Adding New Assets**
1. Add to appropriate `assets/` subdirectory
2. Update asset references in platform code
3. Optimize for target platforms

## 📚 Related Documentation

- [API Documentation](../docs/api/)
- [Backend Development](../backend/README.md)
- [iOS Development](../ios/README.md) (future)
- [Android Development](../android/README.md) (future)
- [Project Structure](../PROJECT_STRUCTURE.md)
