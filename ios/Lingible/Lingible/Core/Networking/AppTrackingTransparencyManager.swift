import Foundation
import SwiftUI
import AppTrackingTransparency
import AdSupport
import GoogleMobileAds

// MARK: - App Tracking Transparency Manager
@MainActor
@preconcurrency
final class AppTrackingTransparencyManager: ObservableObject {

    // MARK: - Published Properties
    @Published var trackingStatus: ATTrackingManager.AuthorizationStatus = .notDetermined
    @Published var hasRequestedPermission = false

    // MARK: - Private Properties
    private let userDefaults = UserDefaults.standard
    private let hasRequestedKey = "ATTrackingManager_hasRequestedPermission"

    // MARK: - Initialization
    init() {
        loadTrackingStatus()
    }

    // MARK: - Public Methods

    /// Request tracking permission from user
    func requestTrackingPermission() async {
        // Check if we've already requested permission
        if hasRequestedPermission {
            print("📱 ATT: Permission already requested, current status: \(trackingStatus.rawValue)")
            return
        }

        // Check if ATT is available (iOS 14+)
        guard #available(iOS 14, *) else {
            print("📱 ATT: Not available on this iOS version")
            trackingStatus = .authorized // Assume authorized for older iOS versions
            return
        }

        print("📱 ATT: Requesting tracking permission...")

        // Request permission
        let status = await ATTrackingManager.requestTrackingAuthorization()

        // Update status
        await MainActor.run {
            self.trackingStatus = status
            self.hasRequestedPermission = true
            self.saveTrackingStatus()
        }

        print("📱 ATT: Permission result: \(status.rawValue)")

        // Configure AdMob based on permission
        configureAdMobForTracking(status)
    }

    /// Get current tracking status
    func getCurrentTrackingStatus() -> ATTrackingManager.AuthorizationStatus {
        if #available(iOS 14, *) {
            return ATTrackingManager.trackingAuthorizationStatus
        } else {
            return .authorized // Assume authorized for older iOS versions
        }
    }

    /// Check if tracking is authorized
    var isTrackingAuthorized: Bool {
        return trackingStatus == .authorized
    }

    /// Get IDFA (Identifier for Advertisers) if authorized
    var advertisingIdentifier: String? {
        guard isTrackingAuthorized else {
            print("📱 ATT: Tracking not authorized, cannot access IDFA")
            return nil
        }

        let idfa = ASIdentifierManager.shared().advertisingIdentifier
        return idfa.uuidString != "00000000-0000-0000-0000-000000000000" ? idfa.uuidString : nil
    }

    /// Check if we should show the permission request
    var shouldShowPermissionRequest: Bool {
        return !hasRequestedPermission && trackingStatus == .notDetermined
    }

    // MARK: - Private Methods

    private func loadTrackingStatus() {
        hasRequestedPermission = userDefaults.bool(forKey: hasRequestedKey)
        trackingStatus = getCurrentTrackingStatus()

        print("📱 ATT: Loaded status - Requested: \(hasRequestedPermission), Status: \(trackingStatus.rawValue)")
    }

    private func saveTrackingStatus() {
        userDefaults.set(hasRequestedPermission, forKey: hasRequestedKey)
        userDefaults.synchronize()
    }

    private func configureAdMobForTracking(_ status: ATTrackingManager.AuthorizationStatus) {
        switch status {
        case .authorized:
            print("📱 ATT: Tracking authorized, enabling personalized ads")
            // AdMob will automatically use personalized ads when tracking is authorized

        case .denied, .restricted:
            print("📱 ATT: Tracking denied/restricted, using non-personalized ads")
            // Configure AdMob for non-personalized ads
            let request = Request()
            let extras = Extras()
            extras.additionalParameters = ["npa": "1"] // Non-personalized ads
            request.register(extras)

        case .notDetermined:
            print("📱 ATT: Tracking not determined, using default behavior")

        @unknown default:
            print("📱 ATT: Unknown tracking status: \(status.rawValue)")
        }
    }
}

// MARK: - ATT Status Extensions
extension ATTrackingManager.AuthorizationStatus {
    var displayName: String {
        switch self {
        case .notDetermined:
            return "Not Determined"
        case .restricted:
            return "Restricted"
        case .denied:
            return "Denied"
        case .authorized:
            return "Authorized"
        @unknown default:
            return "Unknown"
        }
    }

    var description: String {
        switch self {
        case .notDetermined:
            return "User hasn't been asked for permission yet"
        case .restricted:
            return "Tracking is restricted (e.g., parental controls)"
        case .denied:
            return "User denied tracking permission"
        case .authorized:
            return "User authorized tracking"
        @unknown default:
            return "Unknown status"
        }
    }
}

// MARK: - SwiftUI Integration
extension AppTrackingTransparencyManager {

    /// Create a permission request view
    @ViewBuilder
    func createPermissionRequestView() -> some View {
        ATTPrivacyView(attManager: self)
    }

    /// Get permission request message
    var permissionRequestMessage: String {
        return """
        Lingible would like to show you personalized ads to help keep the app free.

        This helps us:
        • Show relevant ads based on your interests
        • Keep the app free for everyone
        • Improve your ad experience

        You can change this setting anytime in your device's Privacy & Security settings.
        """
    }
}

// MARK: - Testing Helpers
#if DEBUG
extension AppTrackingTransparencyManager {

    /// Simulate different tracking statuses for testing
    func simulateTrackingStatus(_ status: ATTrackingManager.AuthorizationStatus) {
        trackingStatus = status
        hasRequestedPermission = true
        saveTrackingStatus()

        print("🧪 ATT: Simulated tracking status: \(status.displayName)")
    }

    /// Reset permission request for testing
    func resetPermissionRequest() {
        hasRequestedPermission = false
        trackingStatus = .notDetermined
        userDefaults.removeObject(forKey: hasRequestedKey)
        userDefaults.synchronize()

        print("🧪 ATT: Reset permission request for testing")
    }
}
#endif
