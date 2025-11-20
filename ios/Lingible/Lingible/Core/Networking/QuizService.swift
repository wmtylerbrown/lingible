import Foundation
import LingibleAPI

// MARK: - Quiz Service Protocol
protocol QuizServiceProtocol {
    func getQuizHistory() async throws -> QuizHistory
    func getNextQuestion(difficulty: QuizDifficulty?) async throws -> QuizQuestionResponse
    func submitAnswer(request: QuizAnswerRequest) async throws -> QuizAnswerResponse
    func getProgress(sessionId: String) async throws -> QuizSessionProgress
    func endSession(sessionId: String) async throws -> QuizResult
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
            // Parse structured error response
            if let quizError = parseError(error) {
                throw quizError
            }
            throw QuizError.networkError(error)
        }
    }

    func getNextQuestion(difficulty: QuizDifficulty? = nil) async throws -> QuizQuestionResponse {
        // Check if user is authenticated
        guard try await getCurrentUser() != nil else {
            throw QuizError.unauthorized
        }

        // Get access token using AuthenticationService
        let accessToken = try await authenticationService.getAuthToken()

        // Debug: Log token info
        print("🔍 QuizService.getNextQuestion: Token length: \(accessToken.count)")
        print("🔍 QuizService.getNextQuestion: Token preview: \(String(accessToken.prefix(50)))...")
        let tokenParts = accessToken.components(separatedBy: ".")
        print("🔍 QuizService.getNextQuestion: Token parts: \(tokenParts.count)")

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        // Debug: Verify header was set
        if let setHeader = LingibleAPIAPI.customHeaders["Authorization"] {
            print("🔍 QuizService.getNextQuestion: Authorization header set (length: \(setHeader.count))")
            print("🔍 QuizService.getNextQuestion: Header preview: \(String(setHeader.prefix(60)))...")
        } else {
            print("❌ QuizService.getNextQuestion: Authorization header NOT set!")
        }

        // Convert QuizDifficulty to API enum (default to beginner)
        let apiDifficulty: QuizAPI.Difficulty_quizQuestionGet? = {
            guard let difficulty = difficulty else {
                return .beginner
            }
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
            return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<QuizQuestionResponse, Error>) in
                QuizAPI.quizQuestionGet(difficulty: apiDifficulty) { data, error in
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
            // Parse structured error response
            if let quizError = parseError(error) {
                throw quizError
            }
            throw QuizError.networkError(error)
        }
    }

    func submitAnswer(request: QuizAnswerRequest) async throws -> QuizAnswerResponse {
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
            return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<QuizAnswerResponse, Error>) in
                QuizAPI.quizAnswerPost(quizAnswerRequest: request) { data, error in
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
            // Parse structured error response
            if let quizError = parseError(error) {
                throw quizError
            }
            throw QuizError.networkError(error)
        }
    }

    func getProgress(sessionId: String) async throws -> QuizSessionProgress {
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
            return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<QuizSessionProgress, Error>) in
                QuizAPI.quizProgressGet(sessionId: sessionId) { data, error in
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
            // Parse structured error response
            if let quizError = parseError(error) {
                throw quizError
            }
            throw QuizError.networkError(error)
        }
    }

    func endSession(sessionId: String) async throws -> QuizResult {
        // Check if user is authenticated
        guard try await getCurrentUser() != nil else {
            throw QuizError.unauthorized
        }

        // Get access token using AuthenticationService
        let accessToken = try await authenticationService.getAuthToken()

        // Configure API client with auth token
        configureAPIClient(with: accessToken)

        // Create end request
        let endRequest = QuizEndRequest(sessionId: sessionId)

        do {
            // Make API call using the generated API
            return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<QuizResult, Error>) in
                QuizAPI.quizEndPost(quizEndRequest: endRequest) { data, error in
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
            // Parse structured error response
            if let quizError = parseError(error) {
                throw quizError
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
        // Validate token format before setting header
        let tokenParts = accessToken.components(separatedBy: ".")
        if tokenParts.count != 3 {
            print("⚠️ QuizService: Invalid token format - expected JWT with 3 parts, got \(tokenParts.count) parts")
            print("⚠️ QuizService: Token preview: \(String(accessToken.prefix(50)))...")
        } else {
            print("✅ QuizService: Token format valid (3 parts)")
        }

        // Configure the global API client with authorization header
        let authHeader = "Bearer \(accessToken)"
        LingibleAPIAPI.customHeaders["Authorization"] = authHeader
        print("🔑 QuizService: Set Authorization header (length: \(authHeader.count))")
    }

    // MARK: - Error Parsing

    /// Parses API error responses and converts them to QuizError
    /// Follows the same pattern as TranslationView for consistent error handling
    private func parseError(_ error: Error) -> QuizError? {
        // Log the error for debugging
        print("🔍 QuizService.parseError: Starting error parsing")
        print("🔍 QuizService.parseError: Error type: \(type(of: error))")
        let errorAsNSError = error as NSError
        print("🔍 QuizService.parseError: NSError domain: \(errorAsNSError.domain), code: \(errorAsNSError.code)")
        print("🔍 QuizService.parseError: NSError description: \(errorAsNSError.localizedDescription)")
        print("🔍 QuizService.parseError: NSError userInfo: \(errorAsNSError.userInfo)")

        // Check if it's an ErrorResponse from the generated API client
        if case let ErrorResponse.error(statusCode, data, response, underlyingError) = error {
            print("🔍 QuizService.parseError: ErrorResponse detected")
            print("🔍 QuizService.parseError: Status code: \(statusCode)")

            // Don't parse successful responses (200) as errors
            if statusCode == 200 {
                print("🔍 QuizService.parseError: Skipping status 200 (success response, not an error)")
                return nil
            }

            if let httpResponse = response as? HTTPURLResponse {
                print("🔍 QuizService.parseError: HTTP status: \(httpResponse.statusCode)")
            }

            print("🔍 QuizService.parseError: Underlying error: \(underlyingError)")
            if let data = data {
                print("🔍 QuizService.parseError: Data length: \(data.count) bytes")
                if let dataString = String(data: data, encoding: .utf8) {
                    print("🔍 QuizService.parseError: Data content: \(dataString)")
                } else {
                    print("🔍 QuizService.parseError: Could not decode data as UTF-8 string")
                }

                // Try to parse as ModelErrorResponse to get structured error info
                do {
                    let decoder = JSONDecoder()
                    decoder.dateDecodingStrategy = .iso8601
                    let errorResponse = try decoder.decode(ModelErrorResponse.self, from: data)
                    print("🔍 QuizService.parseError: ✅ Successfully parsed ModelErrorResponse")
                    print("🔍 QuizService.parseError: - errorCode: '\(errorResponse.errorCode)'")
                    print("🔍 QuizService.parseError: - statusCode: \(errorResponse.statusCode)")
                    print("🔍 QuizService.parseError: - message: '\(errorResponse.message)'")
                    if let details = errorResponse.details {
                        print("🔍 QuizService.parseError: - details: \(details)")
                    }

                    // Check for specific error codes
                    let errorCode = errorResponse.errorCode.lowercased()
                    print("🔍 QuizService.parseError: Checking error code (lowercased): '\(errorCode)'")

                    switch errorCode {
                    case "quiz_daily_limit_reached", "auth_003", "usagelimitexceedederror":
                        print("🔍 QuizService.parseError: ✅ Matched error code '\(errorCode)' -> dailyLimitReached")
                        return .dailyLimitReached

                    case "invalidtokenerror", "tokenexpirederror", "auth_001", "auth_002":
                        print("🔍 QuizService.parseError: ✅ Matched error code '\(errorCode)' -> unauthorized")
                        return .unauthorized

                    default:
                        print("🔍 QuizService.parseError: ⚠️ Error code '\(errorCode)' not in switch, checking details and status code")

                        // Check details for error_type
                        if let details = errorResponse.details?.value as? [String: Any] {
                            print("🔍 QuizService.parseError: Checking details: \(details)")
                            if let errorType = details["error_type"] as? String {
                                print("🔍 QuizService.parseError: Found error_type in details: '\(errorType)'")
                                if errorType == "quiz_daily_limit_reached" {
                                    print("🔍 QuizService.parseError: ✅ Matched error_type -> dailyLimitReached")
                                    return .dailyLimitReached
                                }
                            }
                        }

                        // For other errors, check the status code
                        if errorResponse.statusCode == 401 || errorResponse.statusCode == 403 || errorResponse.statusCode == 429 {
                            print("🔍 QuizService.parseError: Status code is \(errorResponse.statusCode), checking message")
                            let messageLower = errorResponse.message.lowercased()
                            print("🔍 QuizService.parseError: Message (lowercased): '\(messageLower)'")

                            // Check if it's a daily limit by examining the message
                            if messageLower.contains("daily limit") ||
                               messageLower.contains("limit reached") ||
                               messageLower.contains("questions reached") {
                                print("🔍 QuizService.parseError: ✅ Message contains daily limit keywords -> dailyLimitReached")
                                return .dailyLimitReached
                            }
                            print("🔍 QuizService.parseError: ⚠️ Status \(errorResponse.statusCode) but no daily limit in message -> unauthorized")
                            return .unauthorized
                        }
                    }
                } catch let decodeError {
                    // Failed to parse structured error, fall through to check error description
                    print("🔍 QuizService.parseError: ❌ Failed to decode ModelErrorResponse: \(decodeError)")
                    if let dataString = String(data: data, encoding: .utf8) {
                        print("🔍 QuizService.parseError: Raw data that failed to parse: \(dataString)")
                    }
                }
            } else {
                print("🔍 QuizService.parseError: ⚠️ ErrorResponse data is nil")
            }
        } else {
            print("🔍 QuizService.parseError: Not an ErrorResponse, checking as NSError")
        }

        // Fallback: Check error description for common patterns
        print("🔍 QuizService.parseError: Falling back to error description check")
        let nsError = error as NSError
        let description = nsError.localizedDescription.lowercased()
        print("🔍 QuizService.parseError: Error description (lowercased): '\(description)'")

        // Check for authentication errors
        if nsError.domain.contains("Auth") ||
           description.contains("access token") ||
           description.contains("scopes") ||
           description.contains("unauthorized") {
            print("🔍 QuizService.parseError: ✅ Matched authentication pattern -> unauthorized")
            return .unauthorized
        }

        // Check for daily limit in description (fallback)
        if description.contains("daily limit") ||
           description.contains("limit reached") ||
           description.contains("questions reached") ||
           (description.contains("limit") && description.contains("questions")) {
            print("🔍 QuizService.parseError: ✅ Matched daily limit pattern in description -> dailyLimitReached")
            return .dailyLimitReached
        }

        print("🔍 QuizService.parseError: ❌ No match found, returning nil")
        return nil
    }
}

// MARK: - Quiz Errors
enum QuizError: LocalizedError {
    case unauthorized
    case authenticationFailed(String)
    case networkError(Error)
    case invalidResponse
    case dailyLimitReached

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
        }
    }
}
