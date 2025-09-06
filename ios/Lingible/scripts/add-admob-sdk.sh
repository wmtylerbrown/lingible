#!/bin/bash

# Script to add Google Mobile Ads SDK to Xcode project
# This script provides instructions for manually adding the SDK

echo "🔧 Adding Google Mobile Ads SDK to Lingible iOS Project"
echo "=================================================="
echo ""

echo "📋 Manual Steps Required:"
echo ""
echo "1. Open Xcode and open the Lingible project"
echo "2. Go to File → Add Package Dependencies"
echo "3. Enter this URL: https://github.com/googleads/swift-package-manager-google-mobile-ads.git"
echo "4. Click 'Add Package'"
echo "5. Select 'GoogleMobileAds' and click 'Add Package'"
echo "6. Make sure it's added to the 'Lingible' target"
echo ""

echo "📱 Alternative: Use CocoaPods (if you prefer)"
echo "1. Add to Podfile:"
echo "   pod 'Google-Mobile-Ads-SDK'"
echo "2. Run: pod install"
echo "3. Open .xcworkspace file instead of .xcodeproj"
echo ""

echo "✅ After adding the SDK:"
echo "1. Build the project to ensure it compiles"
echo "2. Run the app to test AdMob integration"
echo "3. Check console logs for AdMob initialization messages"
echo ""

echo "🧪 Test Ad Unit IDs (already configured in code):"
echo "Banner: ca-app-pub-3940256099942544/2934735716"
echo "Interstitial: ca-app-pub-3940256099942544/4411468910"
echo ""

echo "📊 Expected Console Output:"
echo "🔧 LingibleApp: Configuring AdMob..."
echo "🔧 AdMobConfig: Initializing AdMob SDK..."
echo "✅ AdMobConfig: AdMob SDK initialized successfully"
echo ""

echo "🎯 Next Steps:"
echo "1. Add the SDK using the steps above"
echo "2. Build and test the app"
echo "3. Check that banner ads appear for free users"
echo "4. Test interstitial ads every 4th translation"
echo "5. Verify premium users see no ads"
echo ""

echo "❓ If you encounter issues:"
echo "1. Check that the SDK is properly linked"
echo "2. Verify the target membership is correct"
echo "3. Clean build folder (⌘+Shift+K) and rebuild"
echo "4. Check console logs for error messages"
echo ""

echo "🚀 Ready to test AdMob integration!"
