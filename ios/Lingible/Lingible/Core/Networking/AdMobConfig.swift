import Foundation
import GoogleMobileAds

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
