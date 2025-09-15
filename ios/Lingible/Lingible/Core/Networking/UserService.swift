import Foundation
import Combine
import LingibleAPI

// MARK: - Notification Names
extension Notification.Name {
    static let dailyRolloverDetected = Notification.Name("dailyRolloverDetected")
}

// MARK: - User Service Protocol
@preconcurrency
protocol UserServiceProtocol: ObservableObject {
    @MainActor var userProfile: UserProfileResponse? { get }
    @MainActor var userUsage: UsageResponse? { get }
    @MainActor var isLoading: Bool { get }
    @MainActor var lastProfileUpdate: Date? { get }
    @MainActor var lastUsageUpdate: Date? { get }

    func loadUserData(forceRefresh: Bool) async
    func refreshUserData() async
    func clearCache()
    func updateUsageFromTranslation(dailyUsed: Int, dailyLimit: Int, tier: UserTier)
    func upgradeUser(_ request: UserUpgradeRequest) async -> Bool
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
        if isLoading {
            return
        }

        // Check cache validity
        let profileCacheValid = isProfileCacheValid
        let usageCacheValid = isUsageCacheValid
        if !forceRefresh && profileCacheValid && usageCacheValid {
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

            // Check for daily rollover on app launch
            checkForDailyRolloverOnLaunch(usage: usage)

            // Update state
            userProfile = profile
            userUsage = usage


        } catch {
            // Log error but continue without user data
            print("Failed to load user data: \(error.localizedDescription)")
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
        }
    }

    /// Reset local translation count (called on daily rollover)
    nonisolated func resetLocalTranslationCount() {
        Task { @MainActor in
            // Notify AdManager to reset its local count
            NotificationCenter.default.post(name: .dailyRolloverDetected, object: nil)
        }
    }

    nonisolated func updateUsageFromTranslation(dailyUsed: Int, dailyLimit: Int, tier: UserTier) {
        Task { @MainActor in
            guard var currentUsage = userUsage else {
                return
            }

            // Check for daily rollover - if backend dailyUsed is less than our local count, reset occurred
            let previousDailyUsed = currentUsage.dailyUsed
            if dailyUsed < previousDailyUsed {
                resetLocalTranslationCount()
            }

            // Update usage data with values from translation response
            currentUsage.dailyUsed = dailyUsed
            currentUsage.dailyLimit = dailyLimit
            currentUsage.tier = tier.toAPITier()

            // Calculate daily remaining
            currentUsage.dailyRemaining = max(0, dailyLimit - dailyUsed)

            // Update the local state
            userUsage = currentUsage
            lastUsageUpdate = Date()

        }
    }

    func forceReloadData() async {
        clearCache()
        await loadUserData(forceRefresh: true)
    }

    private func checkForDailyRolloverOnLaunch(usage: UsageResponse) {
        // Check if this is a new day since last update
        if let lastUpdate = lastUsageUpdate {
            let calendar = Calendar.current
            if !calendar.isDate(lastUpdate, inSameDayAs: Date()) {
                resetLocalTranslationCount()
            }
        }

        // Also check if backend usage is 0 but we have a non-zero local count
        if usage.dailyUsed == 0 {
            resetLocalTranslationCount()
        }
    }

    // MARK: - Subscription Upgrade
    func upgradeUser(_ request: UserUpgradeRequest) async -> Bool {

        do {
            // Get auth token
            _ = try await authenticationService.getAuthToken()

            // Create upgrade request body
            let upgradeRequest = UpgradeRequest(
                platform: request.provider == .apple ? .apple : .google,
                receiptData: request.receiptData,
                transactionId: request.transactionId
            )

            // Call the upgrade API
            _ = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<UpgradeResponse, Error>) in
                UserAPI.userUpgradePost(upgradeRequest: upgradeRequest) { data, error in
                    if let error = error {
                        continuation.resume(throwing: error)
                    } else if let data = data {
                        continuation.resume(returning: data)
                    } else {
                        continuation.resume(throwing: NSError(domain: "UserUpgradeError", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"]))
                    }
                }
            }


            // Clear cache to force refresh of user data
            clearCache()

            // Refresh user data to get updated tier
            await loadUserData(forceRefresh: true)

            return true

        } catch {
            return false
        }
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

        // Check cache first
        if !forceRefresh && isProfileCacheValid, let profile = userProfile {
            return profile
        }

        let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<UserProfileResponse, Error>) in
            UserAPI.userProfileGet() { data, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else if let data = data {
                    continuation.resume(returning: data)
                } else {
                    continuation.resume(throwing: NSError(domain: "UserProfileError", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"]))
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
            UserAPI.userUsageGet() { data, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else if let data = data {
                    continuation.resume(returning: data)
                } else {
                    continuation.resume(throwing: NSError(domain: "UserUsageError", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"]))
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

// MARK: - UserTier Extension
extension UserTier {
    func toAPITier() -> UsageResponse.Tier {
        switch self {
        case .free:
            return .free
        case .premium:
            return .premium
        }
    }
}
