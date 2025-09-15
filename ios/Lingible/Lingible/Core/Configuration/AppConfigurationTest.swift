#if DEBUG
import Foundation

/// Test file to verify AppConfiguration is working correctly
/// This can be removed after testing
struct AppConfigurationTest {

    static func testConfiguration() {
        print("🔧 Testing AppConfiguration...")
        print("Environment: \(AppConfiguration.currentEnvironment.displayName)")
        print("Website Base URL: \(AppConfiguration.websiteBaseURL)")
        print("Terms URL: \(AppConfiguration.termsOfServiceURL)")
        print("Privacy URL: \(AppConfiguration.privacyPolicyURL)")
        print("Support Email: \(AppConfiguration.supportEmail)")
        print("Help FAQ URL: \(AppConfiguration.helpFAQURL)")
        print("✅ AppConfiguration test complete!")
    }
}
#endif
