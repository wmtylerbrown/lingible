# AdMob Integration Guide - Lingible iOS App

## 🎯 Overview

This document outlines the complete AdMob integration for the Lingible iOS app, including banner ads, interstitial ads, and the new upgrade button strategy.

## 📱 Implementation Summary

### **Ad Strategy**
- **Banner Ads**: Below header on all screens for free users only
- **Interstitial Ads**: Every 4th translation (replaces upgrade popup)
- **Upgrade Button**: Flashy button in header right side for free users
- **Premium Users**: Completely ad-free experience

### **Ad Frequency**
- **Banner**: Always visible for free users
- **Interstitial**: Every 4th translation (4, 8, 12, etc.) but not after daily limit
- **Upgrade Prompt**: Only when daily limit reached (dynamic from user profile)

## 🔧 Technical Implementation

### **Files Added/Modified**

#### **New Files**
- `Core/Networking/AdMobConfig.swift` - AdMob configuration and test setup
- `Core/Networking/BannerAdView.swift` - Banner ad SwiftUI wrapper
- `Core/Networking/InterstitialAdManager.swift` - Interstitial ad management
- `Core/Design/EnhancedHeader.swift` - Header with upgrade button
- `Core/Networking/AdManager.swift` - Centralized ad management service

#### **Modified Files**
- `App/LingibleApp.swift` - Added AdMob initialization
- `App/AppCoordinator.swift` - Added AdManager integration
- `Features/Translation/TranslationView.swift` - Updated with ads and new header

### **AdMob SDK Setup**

#### **1. Add Google Mobile Ads SDK**
```bash
# Run the setup script for instructions
./scripts/add-admob-sdk.sh
```

**Manual Steps:**
1. Open Xcode → File → Add Package Dependencies
2. URL: `https://github.com/googleads/swift-package-manager-google-mobile-ads.git`
3. Select `GoogleMobileAds` and add to `Lingible` target

#### **2. Test Ad Unit IDs**
```swift
// Already configured in AdMobConfig.swift
Banner: "ca-app-pub-3940256099942544/2934735716"
Interstitial: "ca-app-pub-3940256099942544/4411468910"
```

## 🎨 UI/UX Changes

### **Header Layout**
```
┌─────────────────────────────────┐
│ [Logo] Lingible        [Upgrade] │ ← New upgrade button
├─────────────────────────────────┤
│        Banner Ad                │ ← AdMob banner (free users only)
├─────────────────────────────────┤
│        App Content              │
└─────────────────────────────────┘
```

### **Upgrade Button Design**
- **Gradient background** with Lingible primary color
- **Star icon** with "Upgrade" text
- **Press animation** with scale effect
- **Shadow effects** for depth
- **Accessibility labels** for screen readers

### **Banner Ad Integration**
- **Standard 320x50 banner** size
- **Smooth loading animation** with placeholder
- **Error handling** with graceful fallbacks
- **Only visible for free users**

## 📊 Ad Frequency Logic

### **Translation Flow (Example with 10 daily limit)**
1. **Translations 1-3**: Normal flow, banner ad visible
2. **Translation 4**: Show interstitial ad, then result
3. **Translations 5-7**: Normal flow, banner ad visible
4. **Translation 8**: Show interstitial ad, then result
5. **Translations 9-10**: Normal flow, banner ad visible
6. **Translation 10**: Show upgrade prompt when daily limit reached

### **Code Implementation**
```swift
// In TranslationView.swift
appCoordinator.adManager.incrementTranslationCount()

// In AdManager.swift
func incrementTranslationCount() {
    translationCount += 1
    updateAdVisibility()

    // Check if we should show interstitial ad
    if let interstitialManager = interstitialAdManager {
        let adShown = interstitialManager.showAdIfNeeded(translationCount: translationCount)
        if adShown {
            print("📺 AdManager: Interstitial ad shown after \(translationCount) translations")
        }
    }
}
```

## 🔒 User Tier Management

### **Free Users**
- See banner ads on all screens
- See interstitial ads every 4th translation
- See upgrade button in header
- Limited to 10 daily translations

### **Premium Users**
- **No ads whatsoever**
- No upgrade button in header
- 100 daily translations (vs 10 free)
- All premium features

### **Tier Detection**
```swift
// In AdManager.swift
var shouldShowAds: Bool {
    let currentTier = userService.userUsage?.tier ?? .free
    return currentTier == .free
}
```

## 🧪 Testing

### **Test Ad Units**
The app uses Google's test ad units for development:
- **Banner**: `ca-app-pub-3940256099942544/2934735716`
- **Interstitial**: `ca-app-pub-3940256099942544/4411468910`

### **Expected Console Output**
```
🔧 LingibleApp: Configuring AdMob...
🔧 AdMobConfig: Initializing AdMob SDK...
✅ AdMobConfig: AdMob SDK initialized successfully
📊 AdManager: Updated ad visibility - Tier: free, Show Banner: true
📺 AdManager: Interstitial ad shown after 4 translations
```

### **Testing Checklist**
- [ ] Banner ads appear for free users
- [ ] Banner ads hidden for premium users
- [ ] Interstitial ads show every 4th translation
- [ ] Upgrade button appears for free users
- [ ] Upgrade button hidden for premium users
- [ ] Ad loading states work correctly
- [ ] Error handling works for failed ad loads

## 🚀 Production Setup

### **After App Store Approval**
1. **Create AdMob App**: Add your app to AdMob console
2. **Get Real Ad Unit IDs**: Create banner and interstitial ad units
3. **Update Configuration**: Replace test IDs in `AdMobConfig.swift`
4. **Test with Real Ads**: Verify monetization works

### **Ad Unit ID Update**
```swift
// In AdMobConfig.swift - Update these after App Store approval
static let productionBannerAdUnitID = "ca-app-pub-YOUR_REAL_ID/BANNER_ID"
static let productionInterstitialAdUnitID = "ca-app-pub-YOUR_REAL_ID/INTERSTITIAL_ID"
```

## 📈 Revenue Projections

### **With Banner + Interstitial**
- **Banner**: $0.10-$0.50 per 1000 impressions
- **Interstitial**: $1.00-$3.00 per 1000 impressions
- **Combined**: $1.10-$3.50 per 1000 impressions
- **Daily Revenue**: $1.10-$3.50 (1000 users)
- **Monthly Revenue**: $33-$105

### **Optimization Opportunities**
- **A/B test ad frequency** (every 3rd vs 4th translation)
- **Add rewarded video ads** for extra translations
- **Implement native ads** in trending section
- **Smart ad timing** based on user behavior

## 🔧 Troubleshooting

### **Common Issues**

#### **Ads Not Loading**
1. Check internet connection
2. Verify AdMob SDK is properly linked
3. Check console logs for error messages
4. Ensure test device ID is configured

#### **Build Errors**
1. Clean build folder (⌘+Shift+K)
2. Reset package caches
3. Verify Google Mobile Ads SDK is added
4. Check target membership

#### **Ads Not Showing**
1. Verify user tier detection
2. Check `shouldShowAds` logic
3. Ensure AdManager is properly initialized
4. Test with free user account

### **Debug Commands**
```swift
// Force show banner for testing
appCoordinator.adManager.forceShowBanner()

// Simulate translation count
appCoordinator.adManager.simulateTranslationCount(4)

// Force show interstitial
appCoordinator.adManager.showInterstitialAd()
```

## 📚 Resources

- [Google Mobile Ads SDK Documentation](https://developers.google.com/admob/ios/quick-start)
- [AdMob Console](https://apps.admob.com/)
- [Test Ad Unit IDs](https://developers.google.com/admob/ios/test-ads)
- [AdMob Policies](https://support.google.com/admob/answer/6129563)

## 🎯 Next Steps

1. **Add Google Mobile Ads SDK** to Xcode project
2. **Build and test** the app with test ads
3. **Verify ad frequency** and user experience
4. **Submit to App Store** with test ads
5. **Switch to real ads** after approval
6. **Monitor performance** and optimize

---

**Status**: ✅ **Implementation Complete** - Ready for SDK addition and testing
