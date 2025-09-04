import Foundation
import Combine
import LingibleAPI

// MARK: - User Service Protocol
@preconcurrency
protocol UserServiceProtocol: ObservableObject {
    var userProfile: UserProfileResponse? { get }
    var userUsage: UsageResponse? { get }
    var isLoading: Bool { get }
    var lastProfileUpdate: Date? { get }
    var lastUsageUpdate: Date? { get }

    func loadUserData(forceRefresh: Bool) async
    func refreshUserData() async
    func clearCache()
}

// MARK: - User Service Implementation
@MainActor
@preconcurrency
final class UserService: UserServiceProtocol {

    // MARK: - Published Properties
    @Published var userProfile: UserProfileResponse?
    @Published var userUsage: UsageResponse?
    @Published var isLoading = false
    @Published var lastProfileUpdate: Date?
    @Published var lastUsageUpdate: Date?

    // MARK: - Private Properties
    private let authenticationService: AuthenticationServiceProtocol
    private var refreshTask: Task<Void, Never>?

    // Different cache times for different data types
    private let profileCacheExpiration: TimeInterval = 86400 // 24 hours (profile changes rarely)
    private let usageCacheExpiration: TimeInterval = 1800    // 30 minutes (usage changes frequently)

    // MARK: - Initialization
    init(authenticationService: AuthenticationServiceProtocol) {
        self.authenticationService = authenticationService
    }

    // MARK: - Public Methods
    func loadUserData(forceRefresh: Bool = false) async {
        // Check if we're already loading
        if isLoading { return }

        // Check cache validity
        if !forceRefresh && isProfileCacheValid && isUsageCacheValid {
            print("✅ UserService: Using cached data")
            return
        }

        isLoading = true
        defer { isLoading = false }

        do {
            // Get auth token
            let accessToken = try await authenticationService.getAuthToken()
            configureAPIClient(with: accessToken)

            // Load data concurrently
            async let profileTask = loadUserProfile(forceRefresh: forceRefresh)
            async let usageTask = loadUserUsage(forceRefresh: forceRefresh)

            let (profile, usage) = try await (profileTask, usageTask)

            // Update state
            userProfile = profile
            userUsage = usage

            print("✅ UserService: Successfully loaded user data")

        } catch {
            print("❌ UserService: Failed to load user data: \(error)")
        }
    }

    func refreshUserData() async {
        await loadUserData(forceRefresh: true)
    }

    func clearCache() {
        userProfile = nil
        userUsage = nil
        lastProfileUpdate = nil
        lastUsageUpdate = nil
        print("🗑️ UserService: Cache cleared")
    }

    // MARK: - Private Methods
    private var isProfileCacheValid: Bool {
        guard let lastUpdate = lastProfileUpdate else { return false }
        return Date().timeIntervalSince(lastUpdate) < profileCacheExpiration
    }

    private var isUsageCacheValid: Bool {
        guard let lastUpdate = lastUsageUpdate else { return false }
        return Date().timeIntervalSince(lastUpdate) < usageCacheExpiration
    }

    private func configureAPIClient(with accessToken: String) {
        let authHeader = "Bearer \(accessToken)"
        LingibleAPIAPI.customHeaders["Authorization"] = authHeader
    }

    private func loadUserProfile(forceRefresh: Bool) async throws -> UserProfileResponse {
        // Check cache first
        if !forceRefresh && isProfileCacheValid, let profile = userProfile {
            return profile
        }

        let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<UserProfileResponse, Error>) in
            UserAPI.userProfileGet { response, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else if let response = response {
                    continuation.resume(returning: response)
                } else {
                    continuation.resume(throwing: UserServiceError.invalidResponse)
                }
            }
        }

        lastProfileUpdate = Date()
        return response
    }

    private func loadUserUsage(forceRefresh: Bool) async throws -> UsageResponse {
        // Check cache first
        if !forceRefresh && isUsageCacheValid, let usage = userUsage {
            return usage
        }

        let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<UsageResponse, Error>) in
            UserAPI.userUsageGet { response, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else if let response = response {
                    continuation.resume(returning: response)
                } else {
                    continuation.resume(throwing: UserServiceError.invalidResponse)
                }
            }
        }

        lastUsageUpdate = Date()
        return response
    }
}

// MARK: - User Service Errors
enum UserServiceError: LocalizedError {
    case invalidResponse
    case unauthorized

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "You need to sign in to access this data"
        }
    }
}
