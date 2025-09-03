import Foundation
import LingibleAPI

// MARK: - Translation Service Protocol
protocol TranslationServiceProtocol {
    func translate(text: String, direction: TranslationDirection?) async throws -> TranslationResult
}

// MARK: - Translation Service Implementation
final class TranslationService: TranslationServiceProtocol {

    // MARK: - Dependencies
    private let apiClient: TranslationAPI
    private let authenticationService: AuthenticationServiceProtocol

    // MARK: - Initialization
    init(
        apiClient: TranslationAPI = TranslationAPI(),
        authenticationService: AuthenticationServiceProtocol = AuthenticationService()
    ) {
        self.apiClient = apiClient
        self.authenticationService = authenticationService
    }

    // MARK: - Public Methods
    func translate(text: String, direction: TranslationDirection? = nil) async throws -> TranslationResult {
        // Get current user's access token
        guard let user = try await getCurrentUser(),
              let accessToken = user.accessToken else {
            throw TranslationError.unauthorized
        }

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        // Create translation request
        let request = TranslationRequest(
            text: text,
            direction: direction?.rawValue
        )

        do {
            // Make API call
            let response = try await apiClient.translatePost(translationRequest: request)

            // Convert to our domain model
            return TranslationResult(
                originalText: response.originalText ?? text,
                translatedText: response.translatedText ?? "",
                direction: TranslationDirection(rawValue: response.direction ?? "") ?? .genzToStandard
            )

        } catch {
            print("❌ Translation API error: \(error)")
            throw TranslationError.networkError(error)
        }
    }

    // MARK: - Private Methods
    private func getCurrentUser() async throws -> AuthenticatedUser? {
        return try await withCheckedThrowingContinuation { continuation in
            let cancellable = authenticationService.currentUser
                .first()
                .sink { user in
                    continuation.resume(returning: user)
                }

            // Store cancellable to prevent deallocation
            _ = cancellable
        }
    }

    private func configureAPIClient(with accessToken: String) {
        // Configure the API client with authorization header
        // This would typically be done through the API client's configuration
        apiClient.customHeaders = ["Authorization": "Bearer \(accessToken)"]
    }
}

// MARK: - Translation Result
struct TranslationResult {
    let originalText: String
    let translatedText: String
    let direction: TranslationDirection
}

// MARK: - Translation Direction
enum TranslationDirection: String, CaseIterable {
    case genzToStandard = "genz_to_standard"
    case standardToGenz = "standard_to_genz"
}

// MARK: - Translation Errors
enum TranslationError: LocalizedError {
    case unauthorized
    case networkError(Error)
    case invalidResponse
    case textTooLong
    case rateLimitExceeded

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "You need to sign in to translate text"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .invalidResponse:
            return "Invalid response from server"
        case .textTooLong:
            return "Text is too long to translate"
        case .rateLimitExceeded:
            return "You've reached your daily translation limit"
        }
    }
}
