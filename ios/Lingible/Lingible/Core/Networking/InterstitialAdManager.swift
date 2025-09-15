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
        isLoading = true
        isAdReady = false
        lastError = nil

        let request = AdMobConfig.createGADRequest()
        InterstitialAd.load(with: adUnitID, request: request) { [weak self] ad, error in
            DispatchQueue.main.async {
                self?.isLoading = false

                if let error = error {
                    self?.lastError = error
                    self?.isAdReady = false
                    return
                }

                self?.interstitialAd = ad
                self?.interstitialAd?.fullScreenContentDelegate = self
                self?.isAdReady = true
                self?.lastError = nil
            }
        }
    }

    func showAd(onDismissed: (() -> Void)? = nil) -> Bool {
        guard let interstitialAd = interstitialAd, isAdReady else {
            return false
        }

        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootViewController = windowScene.windows.first?.rootViewController else {
            return false
        }

        // Store the callback
        self.onAdDismissed = onDismissed

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
    }

    func adDidDismissFullScreenContent(_ ad: FullScreenPresentingAd) {

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
        lastError = error
        isAdReady = false

        // Try to load the next ad
        preloadNextAd()
    }

    func adDidRecordImpression(_ ad: FullScreenPresentingAd) {
    }

    func adDidRecordClick(_ ad: FullScreenPresentingAd) {
    }
}

// MARK: - Translation Counter Integration
extension InterstitialAdManager {

    /// Check if we should show an interstitial ad based on translation count
    func shouldShowAd(translationCount: Int) -> Bool {
        // Use the passed translation count for ad logic
        let actualTranslationCount = translationCount

        let dailyLimit = userService?.userUsage?.dailyLimit ?? 10

        // Show ad every 4th translation, but not after daily limit
        let shouldShow = actualTranslationCount > 0 &&
                        actualTranslationCount % 4 == 0 &&
                        actualTranslationCount <= dailyLimit


        return shouldShow
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
