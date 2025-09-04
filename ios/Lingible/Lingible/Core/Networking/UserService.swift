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
        print("🔄 UserService: loadUserData called (forceRefresh: \(forceRefresh))")

        // Check if we're already loading
        if isLoading {
            print("⏳ UserService: Already loading, skipping")
            return
        }

        // Check cache validity
        let profileCacheValid = isProfileCacheValid
        let usageCacheValid = isUsageCacheValid
        print("📊 UserService: Cache status - Profile: \(profileCacheValid), Usage: \(usageCacheValid)")

        if !forceRefresh && profileCacheValid && usageCacheValid {
            print("✅ UserService: Using cached data")
            return
        }

        print("🌐 UserService: Loading fresh data from API")
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

    nonisolated func clearCache() {
        Task { @MainActor in
            userProfile = nil
            userUsage = nil
            lastProfileUpdate = nil
            lastUsageUpdate = nil
            print("🗑️ UserService: Cache cleared")
        }
    }

    func forceReloadData() async {
        print("🔄 UserService: Force reloading all data")
        clearCache()
        await loadUserData(forceRefresh: true)
    }

    // MARK: - Private Methods
    private var isProfileCacheValid: Bool {
        guard let lastUpdate = lastProfileUpdate,
              let _ = userProfile else { return false }
        return Date().timeIntervalSince(lastUpdate) < profileCacheExpiration
    }

    private var isUsageCacheValid: Bool {
        guard let lastUpdate = lastUsageUpdate,
              let _ = userUsage else { return false }
        return Date().timeIntervalSince(lastUpdate) < usageCacheExpiration
    }

    private func configureAPIClient(with accessToken: String) {
        let authHeader = "Bearer \(accessToken)"
        LingibleAPIAPI.customHeaders["Authorization"] = authHeader
    }

    private func loadUserProfile(forceRefresh: Bool) async throws -> UserProfileResponse {
        print("👤 UserService: Loading user profile (forceRefresh: \(forceRefresh))")

        // Check cache first
        if !forceRefresh && isProfileCacheValid, let profile = userProfile {
            print("📦 UserService: Using cached profile data")
            return profile
        }

        print("🌐 UserService: Fetching profile from API")
        let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<UserProfileResponse, Error>) in
            UserAPI.userProfileGet { response, error in
                if let error = error {
                    print("❌ UserService: Profile API error: \(error)")
                    continuation.resume(throwing: error)
                } else if let response = response {
                    print("✅ UserService: Profile loaded successfully")
                    continuation.resume(returning: response)
                } else {
                    print("❌ UserService: Profile API returned nil response")
                    continuation.resume(throwing: UserServiceError.invalidResponse)
                }
            }
        }

        lastProfileUpdate = Date()
        return response
    }

    private func loadUserUsage(forceRefresh: Bool) async throws -> UsageResponse {
        print("📊 UserService: Loading user usage (forceRefresh: \(forceRefresh))")

        // Check cache first
        if !forceRefresh && isUsageCacheValid, let usage = userUsage {
            print("📦 UserService: Using cached usage data")
            return usage
        }

        print("🌐 UserService: Fetching usage from API")
        let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<UsageResponse, Error>) in
            UserAPI.userUsageGet { response, error in
                if let error = error {
                    print("❌ UserService: Usage API error: \(error)")
                    continuation.resume(throwing: error)
                } else if let response = response {
                    print("✅ UserService: Usage loaded successfully")
                    continuation.resume(returning: response)
                } else {
                    print("❌ UserService: Usage API returned nil response")
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
