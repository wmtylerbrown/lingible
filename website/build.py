#!/usr/bin/env python3
"""
Build script for the Lingible website.
Generates HTML files and copies assets to the build directory.
"""

import os
import re
import shutil
from pathlib import Path

def markdown_to_html(markdown_content, title):
    """Convert basic Markdown to HTML with custom styling."""

    # HTML template with styling
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lingible - {title}</title>

    <!-- Favicon -->
    <link rel="icon" type="image/png" sizes="192x192" href="lingible-logo-192.png">
    <link rel="icon" type="image/png" sizes="512x512" href="lingible-logo-512.png">
    <link rel="apple-touch-icon" href="lingible-logo-192.png">

    <style>
        /* Navigation Styles */
        .nav-header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }}

        .nav-container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .nav-links {{
            display: flex;
            list-style: none;
            gap: 2rem;
            margin: 0;
            padding: 0;
        }}

        .nav-links a {{
            color: #334155;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s ease;
        }}

        .nav-links a:hover {{
            color: #0EA5E9;
        }}

        .nav-links a.active {{
            color: #0EA5E9;
            font-weight: 600;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #334155;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #334155;
            border-bottom: 3px solid {accent_color};
            padding-bottom: 10px;
        }}
        h2 {{
            color: #334155;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        .last-updated {{
            font-style: italic;
            color: #999;
            margin-bottom: 20px;
        }}
        ul, ol {{
            margin: 1rem 0;
            padding-left: 2rem;
        }}
        li {{
            margin: 0.5rem 0;
        }}
        strong {{
            color: #2c3e50;
        }}
        a {{
            color: {accent_color};
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        blockquote {{
            border-left: 4px solid {accent_color};
            margin: 1rem 0;
            padding: 0.5rem 1rem;
            background: #f8f9fa;
            font-style: italic;
        }}

        /* Responsive Design */
        @media (max-width: 768px) {{
            .nav-links {{
                display: none;
            }}

            .container {{
                padding: 20px 15px;
            }}

            body {{
                padding: 10px;
            }}
        }}
    </style>
</head>
<body>
    <header class="nav-header">
        <div class="nav-container">
            <ul class="nav-links">
                <li><a href="index.html">Home</a></li>
                <li><a href="index.html#features">Features</a></li>
                <li><a href="index.html#pricing">Pricing</a></li>
                <li><a href="terms.html">Terms</a></li>
                <li><a href="privacy.html">Privacy</a></li>
            </ul>
        </div>
    </header>

    <div class="container">
        {content}
    </div>

    <script src="navigation.js"></script>
</body>
</html>"""

    # Simple markdown to HTML conversion
    lines = markdown_content.split('\n')
    result_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append('')
            continue

        # Headers
        if stripped.startswith('# '):
            result_lines.append(f'<h1>{stripped[2:]}</h1>')
        elif stripped.startswith('## '):
            result_lines.append(f'<h2>{stripped[3:]}</h2>')
        elif stripped.startswith('### '):
            result_lines.append(f'<h3>{stripped[4:]}</h3>')
        # Lists
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            result_lines.append(f'<li>{stripped[2:]}</li>')
        # Bold text
        elif '**' in stripped:
            # Simple bold replacement
            bold_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', stripped)
            result_lines.append(f'<p>{bold_text}</p>')
        # Regular paragraphs
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(f'<p>{stripped}</p>')

    # Close any open list
    if in_list:
        result_lines.append('</ul>')

    html_content = '\n'.join(result_lines)

    # Convert line breaks to <br> tags within paragraphs
    html_content = re.sub(r'</p>\s*<p>', '<br><br>', html_content)

    # Determine accent color based on document type using official Lingible colors
    accent_color = "#22D3EE" if "privacy" in title.lower() else "#0EA5E9"

    return html_template.format(
        title=title,
        content=html_content,
        accent_color=accent_color
    )

def generate_legal_pages(shared_dir, build_dir):
    """Generate HTML files from Markdown files."""
    # Files to convert
    legal_dir = shared_dir / "legal"
    files_to_convert = [
        (legal_dir / "TERMS_OF_SERVICE.md", build_dir / "terms.html", "Terms of Service"),
        (legal_dir / "PRIVACY_POLICY.md", build_dir / "privacy.html", "Privacy Policy")
    ]

    for md_file, html_file, title in files_to_convert:
        if not md_file.exists():
            print(f"Warning: {md_file.name} not found, skipping...")
            continue

        print(f"Converting {md_file.name} to {html_file.name}...")

        # Read Markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Convert to HTML
        html_content = markdown_to_html(markdown_content, title)

        # Write HTML file
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ Generated {html_file.name}")

def build_website():
    """Build the complete website."""
    print("🚀 Building Lingible website...")

    # Get directories
    website_dir = Path(__file__).parent
    src_dir = website_dir / "src"
    build_dir = website_dir / "build"
    shared_assets_dir = website_dir.parent / "shared" / "assets"

    # Create build directory
    build_dir.mkdir(exist_ok=True)

    # Copy main HTML file
    print("📄 Copying main HTML file...")
    shutil.copy2(src_dir / "index.html", build_dir / "index.html")

    # Copy navigation script
    print("🧭 Copying navigation script...")
    shutil.copy2(src_dir / "navigation.js", build_dir / "navigation.js")

    # Copy app-ads.txt for AdMob verification
    print("📱 Copying app-ads.txt for AdMob verification...")
    app_ads_file = src_dir / "app-ads.txt"
    if app_ads_file.exists():
        shutil.copy2(app_ads_file, build_dir / "app-ads.txt")
        print("  ✅ Copied app-ads.txt")
    else:
        print("  ⚠️ app-ads.txt not found in src directory")

    # Copy assets from shared directory
    print("🖼️ Copying assets from shared directory...")

    # Copy main app icon (1024x1024)
    icon_source = shared_assets_dir / "ios-assets" / "AppIcon.appiconset" / "icon_1024x1024_1x.png"
    if icon_source.exists():
        shutil.copy2(icon_source, build_dir / "lingible-icon-large.png")
        print("  ✅ Copied lingible-icon-large.png")

    # Copy wordmark (large version)
    wordmark_source = shared_assets_dir / "ios-assets" / "Wordmarks.imageset" / "wordmark_large.png"
    if wordmark_source.exists():
        shutil.copy2(wordmark_source, build_dir / "lingible-wordmark.png")
        print("  ✅ Copied lingible-wordmark.png")

    # Copy logo for navigation (from logo imageset)
    logo_source = shared_assets_dir / "ios-assets" / "LingibleLogo.imageset" / "lingible_logo.png"
    if logo_source.exists():
        shutil.copy2(logo_source, build_dir / "lingible-logo.png")
        print("  ✅ Copied lingible-logo.png")

    # Create favicon files (copy from app icon)
    if icon_source.exists():
        shutil.copy2(icon_source, build_dir / "lingible-logo-192.png")
        shutil.copy2(icon_source, build_dir / "lingible-logo-512.png")
        print("  ✅ Copied favicon files")

    # Generate legal pages
    print("📋 Generating legal pages...")
    shared_dir = website_dir.parent / "shared"
    generate_legal_pages(shared_dir, build_dir)

    print("\n🎉 Website build complete!")
    print(f"📁 Build output: {build_dir}")
    print("\nFiles generated:")
    for file in build_dir.glob("*"):
        print(f"  📄 {file.name}")

if __name__ == "__main__":
    build_website()
