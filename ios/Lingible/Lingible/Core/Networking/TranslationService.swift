import Foundation
import LingibleAPI

// MARK: - Translation Service Protocol
protocol TranslationServiceProtocol {
    func translate(text: String, direction: TranslationDirection?) async throws -> TranslationResult
}

// MARK: - Translation Service Implementation
final class TranslationService: TranslationServiceProtocol {

    // MARK: - Dependencies
    private let authenticationService: AuthenticationServiceProtocol

    // MARK: - Initialization
    init(
        authenticationService: AuthenticationServiceProtocol
    ) {
        self.authenticationService = authenticationService
    }



    // MARK: - Public Methods
    func translate(text: String, direction: TranslationDirection? = nil) async throws -> TranslationResult {
        // Check if user is authenticated
        guard let user = try await getCurrentUser() else {
            throw TranslationError.unauthorized
        }

        // Get access token using AuthenticationService
        let accessToken = try await authenticationService.getAuthToken()

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        // Create translation request
        let request = TranslationRequest(
            text: text,
            direction: direction?.toAPIDirection() ?? .genzToEnglish
        )

        do {
            // Make API call using the generated API
            let response = try await TranslationAPI.translatePost(translationRequest: request)

            // Convert to our domain model
            return TranslationResult(
                originalText: response.originalText ?? text,
                translatedText: response.translatedText ?? "",
                direction: response.direction?.toAppDirection() ?? .genzToStandard
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
        // Configure the global API client with authorization header
        LingibleAPIAPI.customHeaders["Authorization"] = "Bearer \(accessToken)"
    }
}

// MARK: - Translation Result
struct TranslationResult {
    let originalText: String
    let translatedText: String
    let direction: TranslationDirection
}

// MARK: - Translation Direction
enum TranslationDirection: String, CaseIterable, Codable {
    case genzToStandard = "genz_to_english"
    case standardToGenz = "english_to_genz"
}

// MARK: - Direction Conversion Extensions
extension TranslationDirection {
    func toAPIDirection() -> TranslationRequest.Direction {
        switch self {
        case .genzToStandard:
            return .genzToEnglish
        case .standardToGenz:
            return .englishToGenz
        }
    }
}

extension TranslationResponse.Direction {
    func toAppDirection() -> TranslationDirection {
        switch self {
        case .genzToEnglish:
            return .genzToStandard
        case .englishToGenz:
            return .standardToGenz
        }
    }
}

// MARK: - Translation Errors
enum TranslationError: LocalizedError {
    case unauthorized
    case authenticationFailed(String)
    case networkError(Error)
    case invalidResponse
    case textTooLong
    case rateLimitExceeded

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "You need to sign in to translate text"
        case .authenticationFailed(let message):
            return "Authentication failed: \(message)"
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
