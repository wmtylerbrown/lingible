import Foundation
import GoogleMobileAds

// MARK: - AdMob Configuration
struct AdMobConfig {
    
    // MARK: - Test Ad Unit IDs (for development)
    static let testBannerAdUnitID = "ca-app-pub-3940256099942544/2934735716"
    static let testInterstitialAdUnitID = "ca-app-pub-3940256099942544/4411468910"
    
    // MARK: - Production Ad Unit IDs (to be set after App Store approval)
    // TODO: Replace with real ad unit IDs from AdMob console after app is approved
    static let productionBannerAdUnitID = "ca-app-pub-3940256099942544/2934735716" // Placeholder
    static let productionInterstitialAdUnitID = "ca-app-pub-3940256099942544/4411468910" // Placeholder
    
    // MARK: - Current Ad Unit IDs (switches based on build configuration)
    static var bannerAdUnitID: String {
        #if DEBUG
        return testBannerAdUnitID
        #else
        return productionBannerAdUnitID
        #endif
    }
    
    static var interstitialAdUnitID: String {
        #if DEBUG
        return testInterstitialAdUnitID
        #else
        return productionInterstitialAdUnitID
        #endif
    }
    
    // MARK: - AdMob Initialization
    static func initialize() {
        print("🔧 AdMobConfig: Initializing AdMob SDK...")
        
        MobileAds.shared.start { status in
            print("✅ AdMobConfig: AdMob SDK initialized successfully")
            print("📊 AdMobConfig: Adapter statuses: \(status.adapterStatusesByClassName)")
            
            // Configure test devices for development
            #if DEBUG
            print("🧪 AdMobConfig: Using test ad units for development")
            #endif
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
