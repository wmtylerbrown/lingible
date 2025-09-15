import Foundation
import GoogleMobileAds
import AppTrackingTransparency

// MARK: - AdMob Configuration
struct AdMobConfig {

    // MARK: - Ad Unit IDs from Build Configuration
    static var bannerAdUnitID: String {
        guard let adUnitID = Bundle.main.object(forInfoDictionaryKey: "GAD_BANNER_AD_UNIT_ID") as? String else {
            // Fallback to test ad unit ID if not configured
            return "ca-app-pub-3940256099942544/2934735716"
        }
        return adUnitID
    }

    static var interstitialAdUnitID: String {
        guard let adUnitID = Bundle.main.object(forInfoDictionaryKey: "GAD_INTERSTITIAL_AD_UNIT_ID") as? String else {
            // Fallback to test ad unit ID if not configured
            return "ca-app-pub-3940256099942544/4411468910"
        }
        return adUnitID
    }

    // MARK: - Environment Detection
    static var isUsingTestAds: Bool {
        let environment = Bundle.main.object(forInfoDictionaryKey: "APP_ENVIRONMENT") as? String
        return environment == "dev" || bannerAdUnitID.contains("3940256099942544")
    }

    // MARK: - AdMob Initialization
    static func initialize() {
        MobileAds.shared.start { status in
            if isUsingTestAds {
                // Test ads initialized
            }
        }
    }

    // MARK: - ATT-Aware AdMob Initialization
    static func initializeWithATT() {

        // Check ATT status before initializing
        if #available(iOS 14, *) {
            let attStatus = ATTrackingManager.trackingAuthorizationStatus

            switch attStatus {
            case .authorized:
                initialize()

            case .denied, .restricted:
                configureForNonPersonalizedAds()
                initialize()

            case .notDetermined:
                initialize()

            @unknown default:
                initialize()
            }
        } else {
            // iOS 13 and below - no ATT required
            initialize()
        }
    }

    // MARK: - Non-Personalized Ads Configuration
    static func configureForNonPersonalizedAds() {
        // Store this configuration for use in ad requests
        UserDefaults.standard.set(true, forKey: "AdMob_NonPersonalizedAds")
        UserDefaults.standard.synchronize()
    }

    // MARK: - Personalized Ads Configuration
    static func configureForPersonalizedAds() {
        // Remove non-personalized ads configuration
        UserDefaults.standard.removeObject(forKey: "AdMob_NonPersonalizedAds")
        UserDefaults.standard.synchronize()
    }

    // MARK: - Check if Non-Personalized Ads
    static var isUsingNonPersonalizedAds: Bool {
        return UserDefaults.standard.bool(forKey: "AdMob_NonPersonalizedAds")
    }

    // MARK: - Create GADRequest with ATT Configuration
    static func createGADRequest() -> Request {
        let request = Request()

        if isUsingNonPersonalizedAds {
            let extras = Extras()
            extras.additionalParameters = ["npa": "1"]
            request.register(extras)
        }

        return request
    }

}

// MARK: - Test Device Configuration
#if DEBUG
extension AdMobConfig {
    static func configureTestDevices() {
        // Get the current device ID for testing
        _ = MobileAds.shared.requestConfiguration.testDeviceIdentifiers

        // Add your device ID to the test devices list
        // You can find your device ID in the console logs when running the app
        MobileAds.shared.requestConfiguration.testDeviceIdentifiers = [
            // Add your device ID here
            // "YOUR_DEVICE_ID_HERE"
        ]
    }
}
#endif

// MARK: - AdMob Error Handling
enum AdMobError: LocalizedError {
    case initializationFailed
    case adLoadFailed
    case adDisplayFailed

    var errorDescription: String? {
        switch self {
        case .initializationFailed:
            return "Failed to initialize AdMob SDK"
        case .adLoadFailed:
            return "Failed to load advertisement"
        case .adDisplayFailed:
            return "Failed to display advertisement"
        }
    }
}
