import Foundation
import LingibleAPI

// MARK: - Quiz Service Protocol
protocol QuizServiceProtocol {
    func getQuizHistory() async throws -> QuizHistory
    func generateChallenge(difficulty: QuizDifficulty, questionCount: Int) async throws -> QuizChallenge
    func submitQuiz(challengeId: String, answers: [QuizAnswer], timeTakenSeconds: Int) async throws -> QuizResult
}

// MARK: - Quiz Service Implementation
final class QuizService: QuizServiceProtocol {

    // MARK: - Dependencies
    private let authenticationService: AuthenticationServiceProtocol

    // MARK: - Initialization
    init(
        authenticationService: AuthenticationServiceProtocol
    ) {
        self.authenticationService = authenticationService
    }

    // MARK: - Public Methods

    func getQuizHistory() async throws -> QuizHistory {
        // Check if user is authenticated
        guard try await getCurrentUser() != nil else {
            throw QuizError.unauthorized
        }

        // Get access token using AuthenticationService
        let accessToken = try await authenticationService.getAuthToken()

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        do {
            // Make API call using the generated API
            return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<QuizHistory, Error>) in
                QuizAPI.quizHistoryGet { data, error in
                    if let error = error {
                        continuation.resume(throwing: error)
                    } else if let data = data {
                        continuation.resume(returning: data)
                    } else {
                        continuation.resume(throwing: NSError(domain: "QuizError", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"]))
                    }
                }
            }
        } catch {
            // Check if it's an authentication/authorization error
            let nsError = error as NSError
            if nsError.domain.contains("Auth") || nsError.localizedDescription.contains("Access Token") || nsError.localizedDescription.contains("scopes") {
                throw QuizError.unauthorized
            }
            throw QuizError.networkError(error)
        }
    }

    func generateChallenge(difficulty: QuizDifficulty, questionCount: Int) async throws -> QuizChallenge {
        // Check if user is authenticated
        guard try await getCurrentUser() != nil else {
            throw QuizError.unauthorized
        }

        // Get access token using AuthenticationService
        let accessToken = try await authenticationService.getAuthToken()

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        // Convert QuizDifficulty to API enum
        let apiDifficulty: QuizAPI.Difficulty_quizChallengeGet = {
            switch difficulty {
            case .beginner:
                return .beginner
            case .intermediate:
                return .intermediate
            case .advanced:
                return .advanced
            }
        }()

        do {
            // Make API call using the generated API
            return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<QuizChallenge, Error>) in
                QuizAPI.quizChallengeGet(difficulty: apiDifficulty, type: .multipleChoice, count: questionCount) { data, error in
                    if let error = error {
                        continuation.resume(throwing: error)
                    } else if let data = data {
                        continuation.resume(returning: data)
                    } else {
                        continuation.resume(throwing: NSError(domain: "QuizError", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"]))
                    }
                }
            }
        } catch {
            // Check if it's an authentication/authorization error
            let nsError = error as NSError
            if nsError.domain.contains("Auth") || nsError.localizedDescription.contains("Access Token") || nsError.localizedDescription.contains("scopes") {
                throw QuizError.unauthorized
            }
            // Check for daily limit errors
            if nsError.localizedDescription.contains("limit") || nsError.localizedDescription.contains("Daily") {
                throw QuizError.dailyLimitReached
            }
            throw QuizError.networkError(error)
        }
    }

    func submitQuiz(challengeId: String, answers: [QuizAnswer], timeTakenSeconds: Int) async throws -> QuizResult {
        // Check if user is authenticated
        guard try await getCurrentUser() != nil else {
            throw QuizError.unauthorized
        }

        // Get access token using AuthenticationService
        let accessToken = try await authenticationService.getAuthToken()

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        // Create submission request
        let submissionRequest = QuizSubmissionRequest(
            challengeId: challengeId,
            answers: answers,
            timeTakenSeconds: timeTakenSeconds
        )

        do {
            // Make API call using the generated API
            return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<QuizResult, Error>) in
                QuizAPI.quizSubmitPost(quizSubmissionRequest: submissionRequest) { data, error in
                    if let error = error {
                        continuation.resume(throwing: error)
                    } else if let data = data {
                        continuation.resume(returning: data)
                    } else {
                        continuation.resume(throwing: NSError(domain: "QuizError", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"]))
                    }
                }
            }
        } catch {
            // Check if it's an authentication/authorization error
            let nsError = error as NSError
            if nsError.domain.contains("Auth") || nsError.localizedDescription.contains("Access Token") || nsError.localizedDescription.contains("scopes") {
                throw QuizError.unauthorized
            }
            // Check for invalid challenge errors
            if nsError.localizedDescription.contains("Invalid") || nsError.localizedDescription.contains("expired") {
                throw QuizError.invalidChallenge
            }
            throw QuizError.networkError(error)
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

// MARK: - Quiz Errors
enum QuizError: LocalizedError {
    case unauthorized
    case authenticationFailed(String)
    case networkError(Error)
    case invalidResponse
    case dailyLimitReached
    case invalidChallenge

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "You need to sign in to take quizzes"
        case .authenticationFailed(let message):
            return "Authentication failed: \(message)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .invalidResponse:
            return "Invalid response from server"
        case .dailyLimitReached:
            return "Daily quiz limit reached. Upgrade to Premium for unlimited quizzes!"
        case .invalidChallenge:
            return "This quiz has expired or is invalid. Please start a new quiz."
        }
    }
}
