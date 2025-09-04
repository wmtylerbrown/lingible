import Foundation

/// App configuration that determines environment-specific settings
struct AppConfiguration {

    /// Environment types
    enum Environment: String, CaseIterable {
        case development = "dev"
        case production = "prod"

        var displayName: String {
            switch self {
            case .development:
                return "Development"
            case .production:
                return "Production"
            }
        }
    }

    /// Current environment based on bundle identifier
    static var currentEnvironment: Environment {
        let bundleId = Bundle.main.bundleIdentifier ?? ""

        if bundleId.contains(".dev") {
            return .development
        } else {
            return .production
        }
    }

    /// Base URL for the website based on environment
    static var websiteBaseURL: String {
        switch currentEnvironment {
        case .development:
            return "https://dev.lingible.com"
        case .production:
            return "https://lingible.com"
        }
    }

    /// Terms of Service URL
    static var termsOfServiceURL: String {
        return "\(websiteBaseURL)/terms.html"
    }

    /// Privacy Policy URL
    static var privacyPolicyURL: String {
        return "\(websiteBaseURL)/privacy.html"
    }

    /// Support email based on environment
    static var supportEmail: String {
        switch currentEnvironment {
        case .development:
            return "support-dev@lingible.com"
        case .production:
            return "support@lingible.com"
        }
    }

    /// Help/FAQ URL based on environment
    static var helpFAQURL: String {
        switch currentEnvironment {
        case .development:
            return "\(websiteBaseURL)/help"
        case .production:
            return "\(websiteBaseURL)/help"
        }
    }
}
