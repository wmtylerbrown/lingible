# Lingible Assets Directory

This directory contains all shared assets for the Lingible project, organized by platform and use case.

## Directory Structure

```
shared/assets/
├── branding/              # Brand guidelines and documentation
│   ├── lingible_full_brand_guide.html
│   └── BRAND_GUIDE_README.md
├── fonts/                 # Typography assets
├── images/                # General image assets
│   ├── icons/            # Icon assets
│   ├── illustrations/    # Illustration assets
│   └── logos/            # Logo variations
├── ios-assets/           # iOS app specific assets
│   ├── AppIcon.appiconset/     # App icons (all sizes)
│   ├── LingibleLogo.imageset/  # Main logo
│   ├── WordmarkMedium.imageset/ # Medium wordmark
│   └── Wordmarks.imageset/     # Large wordmarks
└── web/                  # Web-specific assets (future use)
```

## Asset Usage

### iOS App Assets
- **App Icons**: `ios-assets/AppIcon.appiconset/` - All iOS app icon sizes
- **Logo**: `ios-assets/LingibleLogo.imageset/` - Main app logo
- **Wordmarks**: `ios-assets/Wordmarks.imageset/` - Large wordmarks for headers

### Website Assets
The website build process automatically copies assets from the iOS directory:
- **Hero Icon**: `icon_1024x1024_1x.png` → `lingible-icon-large.png`
- **Wordmark**: `wordmark_large.png` → `lingible-wordmark.png`
- **Logo**: `lingible_logo.png` → `lingible-logo.png`
- **Favicons**: `icon_1024x1024_1x.png` → `lingible-logo-192.png`, `lingible-logo-512.png`

### Brand Guidelines
- **Full Brand Guide**: `branding/lingible_full_brand_guide.html`
- **Brand Documentation**: `branding/BRAND_GUIDE_README.md`

## Asset Management

### Adding New Assets
1. **iOS Assets**: Add to appropriate `ios-assets/` subdirectory
2. **Web Assets**: Add to `web/` directory for web-specific assets
3. **General Assets**: Add to `images/` subdirectories
4. **Brand Assets**: Add to `branding/` directory

### Asset Naming Convention
- **iOS**: Follow Apple's asset naming conventions
- **Web**: Use descriptive names with platform prefix (e.g., `lingible-*`)
- **General**: Use descriptive, lowercase names with hyphens

### Build Integration
- **Website Build**: Automatically copies from `ios-assets/` to build directory
- **iOS Build**: Uses assets directly from `ios-assets/`
- **No Duplication**: Single source of truth for all assets

## Color Palette

Official Lingible brand colors (from brand guide):
- **Primary**: `#0EA5E9` (Sky Blue)
- **Secondary**: `#6366F1` (Indigo)
- **Accent**: `#22D3EE` (Cyan)
- **Text**: `#334155` (Slate Gray)
- **Background**: `#FFFFFF` (White)

## File Sizes

### iOS App Icons
- **1024x1024**: App Store icon (330KB)
- **180x180**: iPhone 3x (11KB)
- **120x120**: iPhone 2x (8KB)
- **87x87**: Settings 3x (6KB)
- **60x60**: Notification 3x (4KB)
- **40x40**: Spotlight 3x (3KB)
- **29x29**: Settings 2x (2KB)
- **20x20**: Notification 2x (2KB)

### Wordmarks
- **Large**: 135KB (hero section)
- **Medium**: 4KB (navigation)
- **Small**: 3KB (compact spaces)

## Maintenance

- **Single Source**: All assets stored in one location
- **No Duplication**: Build processes copy from source
- **Version Control**: All assets tracked in git
- **Optimization**: Assets optimized for their use case
- **Documentation**: This README documents organization and usage
