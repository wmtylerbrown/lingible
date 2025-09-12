import Foundation
import GoogleMobileAds
import SwiftUI
import LingibleAPI
import Combine

// MARK: - Interstitial Ad Manager
@MainActor
class InterstitialAdManager: NSObject, ObservableObject {

    // MARK: - Published Properties
    @Published var isAdReady = false
    @Published var isLoading = false
    @Published var lastError: Error?

    // MARK: - Private Properties
    private var interstitialAd: InterstitialAd?
    private let adUnitID: String
    private let userService: (any UserServiceProtocol)?
    private var onAdDismissed: (() -> Void)?

    // MARK: - Initialization
    init(adUnitID: String = AdMobConfig.interstitialAdUnitID, userService: (any UserServiceProtocol)? = nil) {
        self.adUnitID = adUnitID
        self.userService = userService
        super.init()
        loadAd()
    }

    // MARK: - Public Methods
    func loadAd() {
        print("🔄 InterstitialAdManager: Loading interstitial ad...")
        isLoading = true
        isAdReady = false
        lastError = nil

        let request = AdMobConfig.createGADRequest()
        InterstitialAd.load(with: adUnitID, request: request) { [weak self] ad, error in
            DispatchQueue.main.async {
                self?.isLoading = false

                if let error = error {
                    print("❌ InterstitialAdManager: Failed to load ad: \(error.localizedDescription)")
                    self?.lastError = error
                    self?.isAdReady = false
                    return
                }

                print("✅ InterstitialAdManager: Ad loaded successfully")
                self?.interstitialAd = ad
                self?.interstitialAd?.fullScreenContentDelegate = self
                self?.isAdReady = true
                self?.lastError = nil
            }
        }
    }

    func showAd(onDismissed: (() -> Void)? = nil) -> Bool {
        guard let interstitialAd = interstitialAd, isAdReady else {
            print("⚠️ InterstitialAdManager: Ad not ready to show")
            return false
        }

        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootViewController = windowScene.windows.first?.rootViewController else {
            print("❌ InterstitialAdManager: No root view controller found")
            return false
        }

        // Store the callback
        self.onAdDismissed = onDismissed

        print("📺 InterstitialAdManager: Showing interstitial ad")
        interstitialAd.present(from: rootViewController)
        return true
    }

    func preloadNextAd() {
        // Load the next ad in the background
        Task {
            loadAd()
        }
    }
}

// MARK: - GADFullScreenContentDelegate
extension InterstitialAdManager: FullScreenContentDelegate {

    func adWillPresentFullScreenContent(_ ad: FullScreenPresentingAd) {
        print("📺 InterstitialAdManager: Ad will present full screen content")
    }

    func adDidDismissFullScreenContent(_ ad: FullScreenPresentingAd) {
        print("📺 InterstitialAdManager: Ad did dismiss full screen content")

        // Mark ad as no longer ready and preload the next one
        isAdReady = false
        interstitialAd = nil

        // Call the dismissal callback
        onAdDismissed?()
        onAdDismissed = nil

        // Preload the next ad
        preloadNextAd()
    }

    func ad(_ ad: FullScreenPresentingAd, didFailToPresentFullScreenContentWithError error: Error) {
        print("❌ InterstitialAdManager: Failed to present ad: \(error.localizedDescription)")
        lastError = error
        isAdReady = false

        // Try to load the next ad
        preloadNextAd()
    }

    func adDidRecordImpression(_ ad: FullScreenPresentingAd) {
        print("📊 InterstitialAdManager: Ad impression recorded")
    }

    func adDidRecordClick(_ ad: FullScreenPresentingAd) {
        print("👆 InterstitialAdManager: Ad click recorded")
    }
}

// MARK: - Translation Counter Integration
extension InterstitialAdManager {

    /// Check if we should show an interstitial ad based on translation count
    func shouldShowAd(translationCount: Int) -> Bool {
        // Show ad every 4th translation, but not after daily limit
        let dailyLimit = userService?.userUsage?.dailyLimit ?? 10
        return translationCount > 0 &&
               translationCount % 4 == 0 &&
               translationCount <= dailyLimit
    }

    /// Show ad if conditions are met
    func showAdIfNeeded(translationCount: Int, onDismissed: (() -> Void)? = nil) -> Bool {
        if shouldShowAd(translationCount: translationCount) && isAdReady {
            return showAd(onDismissed: onDismissed)
        }
        return false
    }

    /// Get current ad frequency (always every 4th translation)
    var adFrequency: Int {
        return 4 // Always every 4th translation
    }
}
