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

        // Set up daily rollover observation
        setupDailyRolloverObservation()

        // Initialize banner visibility immediately
        updateBannerAdVisibility()
    }

    // MARK: - Public Methods

    /// Update translation count and check if ads should be shown
    func updateTranslationCount(_ count: Int) {
        translationCount = count
        updateAdVisibility()
    }

    /// Check and show interstitial ad when user opens new translation
    func checkAndShowInterstitialAdForNewTranslation() {
        // Always use backend data as single source of truth
        guard let userUsage = userService.userUsage else {
            return
        }

        let currentTranslationCount = userUsage.dailyUsed

        // Check if we should show an interstitial ad
        if let interstitialManager = interstitialAdManager {
            let shouldShow = interstitialManager.shouldShowAd(translationCount: currentTranslationCount)
            let isReady = interstitialManager.isAdReady

            // Actually show the ad if conditions are met
            if shouldShow && isReady {
                _ = interstitialManager.showAd()
            } else if shouldShow && !isReady {
                interstitialManager.loadAd()
            }
        }
    }

    #if DEBUG
    /// Force show interstitial ad (for testing)
    func forceShowInterstitialAd() -> Bool {
        guard let interstitialManager = interstitialAdManager else {
            return false
        }

        if interstitialManager.isAdReady {
            return interstitialManager.showAd()
        } else {
            return false
        }
    }
    #endif

    /// Update ad visibility based on user tier and translation count
    func updateAdVisibility() {
        // Always use backend data as single source of truth
        guard let userUsage = userService.userUsage else {
            // Even if no user data, still update banner visibility
            updateBannerAdVisibility()
            return
        }

        _ = userUsage.dailyUsed

        // Update banner ad visibility based on user tier
        updateBannerAdVisibility()

        // Note: Interstitial ads are now handled when user taps + NEW button
        // This ensures ads show before starting new translations, not after completing them
    }

    /// Update banner visibility when user data becomes available
    func updateBannerVisibilityWhenUserDataAvailable() {
        updateBannerAdVisibility()
    }

    /// Reset translation count (called daily)
    func resetTranslationCount() {
        translationCount = 0
        updateAdVisibility()
    }

    private func updateBannerAdVisibility() {
        // Update banner ad visibility based on user tier only
        if let userUsage = userService.userUsage {
            let tier = userUsage.tier
            print("🟡 AdMob Banner: User tier: \(tier), shouldShowBanner: \(tier == .free)")

            // Show banner ads for free users (regardless of daily usage)
            shouldShowBanner = (tier == .free)
            print("🟡 AdMob Banner: Updated shouldShowBanner to: \(shouldShowBanner)")
        } else {
            print("🔴 AdMob Banner: No user usage data available - defaulting to show banner for free users")
            // Default to showing banner for free users when data isn't available yet
            // This ensures the banner appears immediately for free users
            shouldShowBanner = true
        }
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
        // The user tier will be checked in updateBannerAdVisibility()
    }

    private func setupATTStatusObservation() {
        // Observe ATT status changes and reconfigure ads accordingly
        attManager.$trackingStatus
            .sink { [weak self] status in
                self?.handleATTStatusChange(status)
            }
            .store(in: &cancellables)
    }

    private func setupDailyRolloverObservation() {
        // Listen for daily rollover notifications
        NotificationCenter.default.publisher(for: .dailyRolloverDetected)
            .sink { [weak self] _ in
                self?.handleDailyRollover()
            }
            .store(in: &cancellables)
    }

    private func handleATTStatusChange(_ status: ATTrackingManager.AuthorizationStatus) {

        switch status {
        case .authorized:
            AdMobConfig.configureForPersonalizedAds()

        case .denied, .restricted:
            AdMobConfig.configureForNonPersonalizedAds()

        case .notDetermined:
            // User hasn't made a decision yet, use non-personalized ads as default
            AdMobConfig.configureForNonPersonalizedAds()

        @unknown default:
            // Fallback to non-personalized ads for unknown cases
            AdMobConfig.configureForNonPersonalizedAds()
        }

        // Reload ads with new configuration
        reloadAdsWithNewConfiguration()
    }

    private func handleDailyRollover() {
        resetTranslationCount()
    }

    private func reloadAdsWithNewConfiguration() {
        // Reload banner ads with new ATT configuration
        if shouldShowBanner {
            // The banner will reload automatically when the view updates
        }

        // Reload interstitial ads with new ATT configuration
        interstitialAdManager?.loadAd()
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

    /// Check if user should see ads (always true for free users)
    var shouldShowAds: Bool {
        return shouldShowBanner
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
            .opacity(shouldShowBanner ? 1.0 : 0.0)
            .animation(.easeInOut(duration: 0.3), value: shouldShowBanner)
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
