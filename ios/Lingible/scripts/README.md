# Amplify Configuration Scripts

This directory contains scripts to automatically set up the correct Amplify configuration for different build environments.

## Scripts

### `setup-amplify-config.sh` (Recommended)
Automatically detects the build configuration and sets up the appropriate Amplify config.

**Usage:**
```bash
# For development builds (default)
./scripts/setup-amplify-config.sh

# For production builds
CONFIGURATION=Release ./scripts/setup-amplify-config.sh
```

### `setup-dev-config.sh`
Manually sets up development configuration.

**Usage:**
```bash
./scripts/setup-dev-config.sh
```

### `setup-prod-config.sh`
Manually sets up production configuration.

**Usage:**
```bash
./scripts/setup-prod-config.sh
```

## Build Process

### For Development:
1. Run `./scripts/setup-amplify-config.sh` (or use dev script)
2. Build with Debug configuration
3. App will use development Cognito User Pool

### For Production:
1. Run `CONFIGURATION=Release ./scripts/setup-amplify-config.sh` (or use prod script)
2. Build with Release configuration
3. App will use production Cognito User Pool

## Xcode Integration

To automatically run these scripts during Xcode builds, add a "Run Script Phase" to your target:

1. Open Xcode project
2. Select your target
3. Go to "Build Phases"
4. Click "+" and add "New Run Script Phase"
5. Add this script:
   ```bash
   "${SRCROOT}/scripts/setup-amplify-config.sh"
   ```
6. Move this phase before "Compile Sources"

## Configuration Files

- `amplify_outputs-dev.json` - Development Cognito configuration
- `amplify_outputs-prod.json` - Production Cognito configuration
- `amplify_outputs.json` - Active configuration (copied from above)

## Verification

To verify which configuration is active:
```bash
# Check the User Pool ID in the active config
grep "user_pool_id" Lingible/amplify_outputs.json
```

- Development: `us-east-1_65YoJgNVi`
- Production: `us-east-1_ENGYDDFRb`
