import Foundation
import LingibleAPI

// MARK: - Trending Service Protocol
protocol TrendingServiceProtocol {
    func getTrendingTerms(limit: Int?, category: TrendingTermResponse.Category?, activeOnly: Bool?) async throws -> TrendingListResponse
}

// MARK: - Trending Service Implementation
final class TrendingService: TrendingServiceProtocol {

    // MARK: - Dependencies
    private let authenticationService: AuthenticationServiceProtocol

    // MARK: - Initialization
    init(
        authenticationService: AuthenticationServiceProtocol
    ) {
        self.authenticationService = authenticationService
    }

    // MARK: - Public Methods
    func getTrendingTerms(limit: Int? = nil, category: TrendingTermResponse.Category? = nil, activeOnly: Bool? = nil) async throws -> TrendingListResponse {
        // Check if user is authenticated
        guard try await getCurrentUser() != nil else {
            throw TrendingError.unauthorized
        }

        // Get access token using AuthenticationService
        let accessToken = try await authenticationService.getAuthToken()

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        // Convert app category to API category
        let apiCategory = category?.toAPICategory()

        do {
            // Make API call using the generated API
            return try await TrendingAPI.trendingGet(limit: limit, category: apiCategory, activeOnly: activeOnly)

        } catch {
            // Check if it's an authentication/authorization error
            let nsError = error as NSError
            if nsError.domain.contains("Auth") || nsError.localizedDescription.contains("Access Token") || nsError.localizedDescription.contains("scopes") {
                throw TrendingError.unauthorized
            }
            throw TrendingError.networkError(error)
        }
    }

    // MARK: - Private Methods
    @MainActor
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

// MARK: - Trending Category
enum TrendingCategory: String, CaseIterable, Codable {
    case slang = "slang"
    case meme = "meme"
    case expression = "expression"
    case hashtag = "hashtag"
    case phrase = "phrase"

    var displayName: String {
        switch self {
        case .slang:
            return "Slang"
        case .meme:
            return "Meme"
        case .expression:
            return "Expression"
        case .hashtag:
            return "Hashtag"
        case .phrase:
            return "Phrase"
        }
    }

    var icon: String {
        switch self {
        case .slang:
            return "text.bubble"
        case .meme:
            return "face.smiling"
        case .expression:
            return "quote.bubble"
        case .hashtag:
            return "number"
        case .phrase:
            return "text.quote"
        }
    }
}

// MARK: - Category Conversion Extensions
extension TrendingCategory {
    func toAPICategory() -> TrendingAPI.Category_trendingGet {
        switch self {
        case .slang:
            return .slang
        case .meme:
            return .meme
        case .expression:
            return .expression
        case .hashtag:
            return .hashtag
        case .phrase:
            return .phrase
        }
    }
}

// MARK: - Trending Errors
enum TrendingError: LocalizedError {
    case unauthorized
    case authenticationFailed(String)
    case networkError(Error)
    case invalidResponse
    case categoryNotAvailable
    case limitExceeded

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "You need to sign in to view trending terms"
        case .authenticationFailed(let message):
            return "Authentication failed: \(message)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .invalidResponse:
            return "Invalid response from server"
        case .categoryNotAvailable:
            return "This category is only available for premium users"
        case .limitExceeded:
            return "You've reached your trending terms limit"
        }
    }
}
