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
        print("🔧 AdMobConfig: Initializing AdMob SDK...")
        print("📱 AdMobConfig: Banner Ad Unit ID: \(bannerAdUnitID)")
        print("📱 AdMobConfig: Interstitial Ad Unit ID: \(interstitialAdUnitID)")

        MobileAds.shared.start { status in
            print("✅ AdMobConfig: AdMob SDK initialized successfully")
            print("📊 AdMobConfig: Adapter statuses: \(status.adapterStatusesByClassName)")

            if isUsingTestAds {
                print("🧪 AdMobConfig: Using test ad units for development")
            } else {
                print("💰 AdMobConfig: Using production ad units")
            }
        }
    }

    // MARK: - ATT-Aware AdMob Initialization
    static func initializeWithATT() {
        print("🔧 AdMobConfig: Initializing AdMob SDK with ATT support...")

        // Check ATT status before initializing
        if #available(iOS 14, *) {
            let attStatus = ATTrackingManager.trackingAuthorizationStatus
            print("📱 AdMobConfig: Current ATT status: \(attStatus.rawValue)")

            switch attStatus {
            case .authorized:
                print("📱 AdMobConfig: Tracking authorized, enabling personalized ads")
                initialize()

            case .denied, .restricted:
                print("📱 AdMobConfig: Tracking denied/restricted, configuring for non-personalized ads")
                configureForNonPersonalizedAds()
                initialize()

            case .notDetermined:
                print("📱 AdMobConfig: ATT not determined, will configure after permission request")
                initialize()

            @unknown default:
                print("📱 AdMobConfig: Unknown ATT status, using default configuration")
                initialize()
            }
        } else {
            // iOS 13 and below - no ATT required
            print("📱 AdMobConfig: iOS 13 or below, no ATT required")
            initialize()
        }
    }

    // MARK: - Non-Personalized Ads Configuration
    static func configureForNonPersonalizedAds() {
        print("📱 AdMobConfig: Configuring for non-personalized ads")

        // Set up request configuration for non-personalized ads
        let request = Request()
        let extras = Extras()
        extras.additionalParameters = ["npa": "1"] // Non-personalized ads
        request.register(extras)

        // Store this configuration for use in ad requests
        UserDefaults.standard.set(true, forKey: "AdMob_NonPersonalizedAds")
        UserDefaults.standard.synchronize()
    }

    // MARK: - Personalized Ads Configuration
    static func configureForPersonalizedAds() {
        print("📱 AdMobConfig: Configuring for personalized ads")

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
            print("📱 AdMobConfig: Using non-personalized ad request")
        } else {
            print("📱 AdMobConfig: Using personalized ad request")
        }

        return request
    }

    // MARK: - Test Device Configuration
    static func configureTestDevices() {
        #if DEBUG
        // Get the current device ID for testing
        let deviceID = MobileAds.shared.requestConfiguration.testDeviceIdentifiers
        print("🧪 AdMobConfig: Current test device IDs: \(deviceID ?? [])")

        // Add your device ID to the test devices list
        // You can find your device ID in the console logs when running the app
        MobileAds.shared.requestConfiguration.testDeviceIdentifiers = [
            // Add your device ID here
            // "YOUR_DEVICE_ID_HERE"
        ]
        #endif
    }
}

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
