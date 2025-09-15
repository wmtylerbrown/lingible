import Foundation
import LingibleAPI

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

    /// Base URL for the API based on environment
    static var apiBaseURL: String {
        // Try to get from build configuration first
        if let configURL = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String {
            return configURL
        }

        // Fallback to environment-based logic
        switch currentEnvironment {
        case .development:
            return "https://api.dev.lingible.com"
        case .production:
            return "https://api.lingible.com"
        }
    }

    /// Base URL for the website based on environment
    static var websiteBaseURL: String {
        // Try to get from build configuration first
        if let configURL = Bundle.main.object(forInfoDictionaryKey: "WEBSITE_BASE_URL") as? String {
            return configURL
        }

        // Fallback to environment-based logic
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
        // Try to get from build configuration first
        if let configEmail = Bundle.main.object(forInfoDictionaryKey: "SUPPORT_EMAIL") as? String {
            return configEmail
        }

        // Fallback to environment-based logic
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

    /// Amplify configuration file name based on environment
    static var amplifyConfigFileName: String {
        switch currentEnvironment {
        case .development:
            return "amplifyconfiguration-dev"
        case .production:
            return "amplifyconfiguration-prod"
        }
    }

    /// Amplify outputs file name based on environment
    static var amplifyOutputsFileName: String {
        switch currentEnvironment {
        case .development:
            return "amplify_outputs-dev"
        case .production:
            return "amplify_outputs-prod"
        }
    }

    /// Configure the API client with the correct base URL for the current environment
    static func configureAPI() {
        LingibleAPIAPI.basePath = apiBaseURL
    }
}
