import Foundation
import LingibleAPI

class HistoryService: ObservableObject {
    private let authenticationService: AuthenticationServiceProtocol

    init(authenticationService: AuthenticationServiceProtocol? = nil) {
        self.authenticationService = authenticationService ?? AuthenticationService()
    }

    // MARK: - Public Methods

    func getTranslationHistory(
        limit: Int = 20,
        offset: Int = 0,
        completion: @escaping (Result<TranslationHistoryServiceResult, Error>) -> Void
    ) {
        print("📚 HistoryService: Starting getTranslationHistory - limit: \(limit), offset: \(offset)")

        // Check authentication
        Task {
            do {
                guard let user = await authenticationService.getCurrentUserValue() else {
                    print("❌ HistoryService: User not authenticated")
                    DispatchQueue.main.async {
                        completion(.failure(HistoryError.notAuthenticated))
                    }
                    return
                }

                print("✅ HistoryService: User authenticated - ID: \(user.id)")

                // Get access token
                let accessToken = try await authenticationService.getAuthToken()
                print("🔑 HistoryService: Got access token - length: \(accessToken.count)")

                // Configure API client with auth token
                configureAPIClient(with: accessToken)

                print("🌐 HistoryService: Making API call to translationsGet...")

                // Make API call
                TranslationAPI.translationsGet(limit: limit, offset: offset) { response, error in
                    if let error = error {
                        print("❌ HistoryService: API call failed with error: \(error)")
                        completion(.failure(error))
                        return
                    }

                    guard let response = response else {
                        print("❌ HistoryService: No response received from API")
                        completion(.failure(HistoryError.noResponse))
                        return
                    }

                    print("✅ HistoryService: API call successful - received \(response.translations.count) items")
                    completion(.success(response))
                }
            } catch {
                print("❌ HistoryService: Error in getTranslationHistory: \(error)")
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
    }

    func clearAllHistory(completion: @escaping (Result<SuccessResponse, Error>) -> Void) {
        // Check authentication
        Task {
            do {
                guard await authenticationService.getCurrentUserValue() != nil else {
                    DispatchQueue.main.async {
                        completion(.failure(HistoryError.notAuthenticated))
                    }
                    return
                }

                // Get access token
                let accessToken = try await authenticationService.getAuthToken()

                // Configure API client with auth token
                configureAPIClient(with: accessToken)

                // Make API call
                TranslationAPI.translationsDeleteAllDelete { response, error in
                    if let error = error {
                        completion(.failure(error))
                        return
                    }

                    guard let response = response else {
                        completion(.failure(HistoryError.noResponse))
                        return
                    }

                    completion(.success(response))
                }
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
    }

    func deleteTranslation(
        translationId: String,
        completion: @escaping (Result<SuccessResponse, Error>) -> Void
    ) {
        // Check authentication
        Task {
            do {
                guard await authenticationService.getCurrentUserValue() != nil else {
                    DispatchQueue.main.async {
                        completion(.failure(HistoryError.notAuthenticated))
                    }
                    return
                }

                // Get access token
                let accessToken = try await authenticationService.getAuthToken()

                // Configure API client with auth token
                configureAPIClient(with: accessToken)

                // Make API call
                TranslationAPI.translationsTranslationIdDelete(translationId: translationId) { response, error in
                    if let error = error {
                        completion(.failure(error))
                        return
                    }

                    guard let response = response else {
                        completion(.failure(HistoryError.noResponse))
                        return
                    }

                    completion(.success(response))
                }
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
    }

    // MARK: - Private Methods

    private func configureAPIClient(with accessToken: String) {
        // Configure the global API client with authorization header
        LingibleAPIAPI.customHeaders["Authorization"] = "Bearer \(accessToken)"
    }
}

// MARK: - History Errors

enum HistoryError: LocalizedError {
    case notAuthenticated
    case noResponse
    case premiumRequired
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "You must be logged in to view translation history."
        case .noResponse:
            return "No response received from server."
        case .premiumRequired:
            return "Translation history is only available for premium users."
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}
