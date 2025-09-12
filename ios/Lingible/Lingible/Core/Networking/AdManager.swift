import Foundation
import SwiftUI
import LingibleAPI
import Combine
import AppTrackingTransparency

// MARK: - Ad Manager Service
@MainActor
@preconcurrency
final class AdManager: ObservableObject {

    // MARK: - Published Properties
    @Published var shouldShowBanner = false
    @Published var isBannerLoaded = false
    @Published var interstitialAdManager: InterstitialAdManager?

    // MARK: - Private Properties
    private let userService: any UserServiceProtocol
    private let attManager: AppTrackingTransparencyManager
    private var translationCount = 0
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization
    init(userService: any UserServiceProtocol, attManager: AppTrackingTransparencyManager) {
        self.userService = userService
        self.attManager = attManager
        self.interstitialAdManager = InterstitialAdManager(userService: userService)

        // Initialize AdMob with ATT support
        AdMobConfig.initializeWithATT()

        // Set up user tier observation
        setupUserTierObservation()

        // Set up ATT status observation
        setupATTStatusObservation()
    }

    // MARK: - Public Methods

    /// Update translation count and check if ads should be shown
    func updateTranslationCount(_ count: Int) {
        translationCount = count
        updateAdVisibility()
    }

    /// Increment translation count and check for interstitial ad
    func incrementTranslationCount(onAdDismissed: (() -> Void)? = nil) {
        translationCount += 1
        updateAdVisibility()

        // Check if we should show interstitial ad
        if let interstitialManager = interstitialAdManager {
            let adShown = interstitialManager.showAdIfNeeded(translationCount: translationCount, onDismissed: onAdDismissed)
            if adShown {
                print("📺 AdManager: Interstitial ad shown after \(translationCount) translations")
            }
        }
    }

    /// Reset translation count (called daily)
    func resetTranslationCount() {
        translationCount = 0
        updateAdVisibility()
        print("🔄 AdManager: Translation count reset")
    }

    /// Force show interstitial ad (for testing)
    func showInterstitialAd() -> Bool {
        guard let interstitialManager = interstitialAdManager else { return false }
        return interstitialManager.showAd()
    }

    /// Preload next interstitial ad
    func preloadInterstitialAd() {
        interstitialAdManager?.preloadNextAd()
    }

    // MARK: - Private Methods

    private func setupUserTierObservation() {
        // Since userService is a protocol, we'll update ad visibility when translation count changes
        // The user tier will be checked in updateAdVisibility()
    }

    private func setupATTStatusObservation() {
        // Observe ATT status changes and reconfigure ads accordingly
        attManager.$trackingStatus
            .sink { [weak self] status in
                self?.handleATTStatusChange(status)
            }
            .store(in: &cancellables)
    }

    private func handleATTStatusChange(_ status: ATTrackingManager.AuthorizationStatus) {
        print("📱 AdManager: ATT status changed to \(status.rawValue)")

        switch status {
        case .authorized:
            print("📱 AdManager: Tracking authorized, configuring for personalized ads")
            AdMobConfig.configureForPersonalizedAds()

        case .denied, .restricted:
            print("📱 AdManager: Tracking denied/restricted, configuring for non-personalized ads")
            AdMobConfig.configureForNonPersonalizedAds()

        case .notDetermined:
            print("📱 AdManager: ATT not determined, using default configuration")

        @unknown default:
            print("📱 AdManager: Unknown ATT status: \(status.rawValue)")
        }

        // Reload ads with new configuration
        reloadAdsWithNewConfiguration()
    }

    private func reloadAdsWithNewConfiguration() {
        // Reload banner ads with new ATT configuration
        if shouldShowBanner {
            print("🔄 AdManager: Reloading banner ads with new ATT configuration")
            // The banner will reload automatically when the view updates
        }

        // Reload interstitial ads with new ATT configuration
        interstitialAdManager?.loadAd()
    }

    private func updateAdVisibility() {
        let currentTier = userService.userUsage?.tier ?? .free

        // Only show ads for free users
        shouldShowBanner = currentTier == .free

        print("📊 AdManager: Updated ad visibility - Tier: \(currentTier), Show Banner: \(shouldShowBanner), Should Show Ads: \(shouldShowAds)")
    }
}

// MARK: - AdMob Integration Extensions
extension AdManager {

    /// Get banner ad unit ID
    var bannerAdUnitID: String {
        return AdMobConfig.bannerAdUnitID
    }

    /// Get interstitial ad unit ID
    var interstitialAdUnitID: String {
        return AdMobConfig.interstitialAdUnitID
    }

    /// Check if user should see ads
    var shouldShowAds: Bool {
        let currentTier = userService.userUsage?.tier ?? .free
        return currentTier == .free
    }

    /// Get current translation count
    var currentTranslationCount: Int {
        return translationCount
    }

    /// Check if interstitial ad is ready
    var isInterstitialReady: Bool {
        return interstitialAdManager?.isAdReady ?? false
    }
}

// MARK: - SwiftUI Integration
extension AdManager {

    /// Create banner ad view
    func createBannerAdView() -> some View {
        SwiftUIBannerAd(adUnitID: bannerAdUnitID)
            .opacity(shouldShowAds ? 1.0 : 0.0)
            .animation(.easeInOut(duration: 0.3), value: shouldShowAds)
    }

    /// Create enhanced header with upgrade button
    func createEnhancedHeader(
        title: String? = nil,
        actionButton: HeaderActionButton? = nil,
        onUpgradeTap: (() -> Void)? = nil
    ) -> EnhancedHeader {
        let userTier = userService.userUsage?.tier ?? .free

        return EnhancedHeader(
            title: title,
            actionButton: actionButton,
            userTier: userTier,
            onUpgradeTap: onUpgradeTap
        )
    }
}

// MARK: - Testing Helpers
#if DEBUG
extension AdManager {

    /// Simulate translation count for testing
    func simulateTranslationCount(_ count: Int) {
        translationCount = count
        updateAdVisibility()
    }

    /// Force show banner for testing
    func forceShowBanner() {
        shouldShowBanner = true
    }

    /// Force hide banner for testing
    func forceHideBanner() {
        shouldShowBanner = false
    }
}
#endif
