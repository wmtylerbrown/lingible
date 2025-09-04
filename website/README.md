# Lingible Website

This directory contains the Lingible website source files and build process.

## Directory Structure

```
website/
├── src/                    # Source files
│   ├── index.html         # Main website page
│   └── navigation.js      # Navigation script
├── build/                 # Generated website (auto-created)
│   ├── index.html        # Built main page
│   ├── terms.html        # Generated terms page
│   ├── privacy.html      # Generated privacy page
│   ├── navigation.js     # Navigation script
│   └── *.png             # Assets copied from shared/
└── build.py              # Single build script (does everything)
```

## Build Process

### Single Command Build
```bash
cd website
python build.py
```

The build script handles everything:
- ✅ Copies main HTML file and navigation script
- ✅ Copies assets from shared directory
- ✅ Generates legal pages from Markdown
- ✅ Creates complete website in build/ directory

## Development

### Local Development
1. Make changes to files in `src/`
2. Run `python build.py` to build
3. Test locally: `cd build && python -m http.server 8000`
4. Visit http://localhost:8000

### Legal Pages
- Source files are in `../../shared/legal/TERMS_OF_SERVICE.md` and `../../shared/legal/PRIVACY_POLICY.md`
- HTML versions are auto-generated in `build/`
- Update Markdown files and rebuild to update HTML

## Deployment

The website is automatically deployed to AWS when you run:
```bash
cd backend/infrastructure
npm run build && npm run deploy:dev
```

This creates:
- S3 bucket for static hosting
- CloudFront distribution for CDN
- Automatic deployment of build files

## Assets

### Asset Source
All assets are sourced from `../../shared/assets/ios-assets/` to avoid duplication:
- **Hero Icon**: `AppIcon.appiconset/icon_1024x1024_1x.png` → `lingible-icon-large.png`
- **Wordmark**: `Wordmarks.imageset/wordmark_large.png` → `lingible-wordmark.png`
- **Logo**: `LingibleLogo.imageset/lingible_logo.png` → `lingible-logo.png`
- **Favicons**: `AppIcon.appiconset/icon_1024x1024_1x.png` → `lingible-logo-192.png`, `lingible-logo-512.png`

### Build Process
The build script automatically copies assets from the shared directory, ensuring:
- ✅ **No duplication** - Single source of truth
- ✅ **Consistency** - Same assets used across platforms
- ✅ **Maintainability** - Update once, use everywhere

### Brand Colors
- Primary: `#0EA5E9` (Sky Blue)
- Secondary: `#6366F1` (Indigo)
- Accent: `#22D3EE` (Cyan)
- Text: `#334155` (Slate Gray)
- Background: `#FFFFFF` (White)

## Features

- ✅ Responsive design for all devices
- ✅ Official Lingible branding and colors
- ✅ Legal pages with consistent navigation
- ✅ SEO-optimized with proper meta tags
- ✅ Fast loading with optimized assets
- ✅ Professional appearance matching mobile app
