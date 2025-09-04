import Foundation
import Combine
import LingibleAPI

// MARK: - Trending ViewModel
@MainActor
final class TrendingViewModel: ObservableObject {

    // MARK: - Published Properties
    @Published var trendingTerms: [TrendingTermResponse] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var selectedCategory: TrendingTermResponse.Category?
    @Published var totalCount: Int = 0
    @Published var lastUpdated: Date?
    @Published var userTier: UserTier = .free

    // MARK: - Private Properties
    private let trendingService: TrendingServiceProtocol
    private let userService: any UserServiceProtocol
    private let authenticationService: AuthenticationServiceProtocol
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Caching Properties
    private var cachedTrendingData: [TrendingTermResponse.Category?: TrendingListResponse] = [:]
    private var lastCacheUpdate: Date?
    private let cacheExpirationTime: TimeInterval = 86400 // 24 hours

    // MARK: - Computed Properties
    var availableCategories: [TrendingTermResponse.Category] {
        switch userTier {
        case .free:
            return [.slang] // Free users only get slang category
        case .premium:
            return TrendingTermResponse.Category.allCases // Premium users get all categories
        }
    }

    var maxLimit: Int {
        switch userTier {
        case .free:
            return 10
        case .premium:
            return 100
        }
    }

    var hasError: Bool {
        errorMessage != nil
    }

    // MARK: - Initialization
    init(
        trendingService: TrendingServiceProtocol,
        userService: any UserServiceProtocol,
        authenticationService: AuthenticationServiceProtocol
    ) {
        self.trendingService = trendingService
        self.userService = userService
        self.authenticationService = authenticationService

        setupUserTierObserver()
    }

    // MARK: - Public Methods
    func loadTrendingTerms() async {
        await loadTrendingTerms(category: selectedCategory)
    }

    func loadTrendingTerms(category: TrendingTermResponse.Category?) async {
        // Update user tier from user profile (handle gracefully if profile fetch fails)
        do {
            if let userProfile = userService.userProfile {
                userTier = userProfile.tier?.toAppTier() ?? .free
            } else {
                // If no user profile available, assume free tier
                userTier = .free
            }
        } catch {
            // If user profile fetch fails, assume free tier and continue
            userTier = .free
        }

        // Validate category access for free users
        if userTier == .free && category != nil && category != .slang {
            errorMessage = "Category filtering is only available for premium users"
            return
        }

        // Check cache first
        if let cachedResponse = getCachedData(for: category) {
            print("✅ TrendingViewModel: Using cached data for category: \(category?.displayName ?? "all")")
            trendingTerms = cachedResponse.terms ?? []
            totalCount = cachedResponse.totalCount ?? 0
            lastUpdated = cachedResponse.lastUpdated
            selectedCategory = category
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await trendingService.getTrendingTerms(
                limit: maxLimit,
                category: category,
                activeOnly: true
            )

            // Cache the response
            setCachedData(response, for: category)

            trendingTerms = response.terms ?? []
            totalCount = response.totalCount ?? 0
            lastUpdated = response.lastUpdated
            selectedCategory = category

            print("📥 TrendingViewModel: Fetched fresh data for category: \(category?.displayName ?? "all")")

        } catch {
            handleError(error)
        }

        isLoading = false
    }

    func selectCategory(_ category: TrendingTermResponse.Category?) {
        selectedCategory = category
        Task {
            await loadTrendingTerms(category: category)
        }
    }

    func refreshTrendingTerms() async {
        // Clear cache to force fresh data
        clearCache()
        await loadTrendingTerms(category: selectedCategory)
    }

    func clearError() {
        errorMessage = nil
    }

    func clearCache() {
        cachedTrendingData.removeAll()
        lastCacheUpdate = nil
        print("🗑️ TrendingViewModel: Cache cleared")
    }

    // MARK: - Private Methods
    private var isCacheValid: Bool {
        guard let lastUpdate = lastCacheUpdate else { return false }
        return Date().timeIntervalSince(lastUpdate) < cacheExpirationTime
    }

    private func getCachedData(for category: TrendingTermResponse.Category?) -> TrendingListResponse? {
        guard isCacheValid else { return nil }
        return cachedTrendingData[category]
    }

    private func setCachedData(_ data: TrendingListResponse, for category: TrendingTermResponse.Category?) {
        cachedTrendingData[category] = data
        lastCacheUpdate = Date()
    }

    private func setupUserTierObserver() {
        // For now, we'll use a simpler approach since UserServiceProtocol doesn't expose publishers
        // We'll update the user tier when the view model loads trending terms
        authenticationService.currentUser
            .map { authenticatedUser in
                // If user is authenticated, we'll determine tier from user profile when loading data
                // For now, default to free and update when we load trending terms
                return UserTier.free
            }
            .assign(to: \.userTier, on: self)
            .store(in: &cancellables)
    }

    private func handleError(_ error: Error) {
        if let trendingError = error as? TrendingError {
            switch trendingError {
            case .categoryNotAvailable:
                errorMessage = "This category is only available for premium users"
            case .limitExceeded:
                errorMessage = "You've reached your trending terms limit. Upgrade to premium for more access."
            case .unauthorized:
                errorMessage = "Please sign in to view trending terms"
            default:
                errorMessage = trendingError.localizedDescription
            }
        } else {
            errorMessage = "Failed to load trending terms: \(error.localizedDescription)"
        }
    }
}

// MARK: - User Tier
enum UserTier: String, CaseIterable {
    case free = "free"
    case premium = "premium"

    var displayName: String {
        switch self {
        case .free:
            return "Free"
        case .premium:
            return "Premium"
        }
    }
}

// MARK: - Tier Conversion Extensions
extension UserProfileResponse.Tier {
    func toAppTier() -> UserTier {
        switch self {
        case .free:
            return .free
        case .premium:
            return .premium
        }
    }
}

// MARK: - Trending Category Extensions
extension TrendingTermResponse.Category {
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
            return "quote.bubble"
        case .meme:
            return "face.smiling"
        case .expression:
            return "text.bubble"
        case .hashtag:
            return "number"
        case .phrase:
            return "text.quote"
        }
    }

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

// MARK: - Trending Term Extensions
extension TrendingTermResponse {
    var popularityPercentage: Int {
        guard let score = popularityScore else { return 0 }
        return Int(score)
    }

    var categoryDisplayName: String {
        guard let category = category else { return "Unknown" }
        return category.displayName
    }

    var categoryIcon: String {
        guard let category = category else { return "questionmark" }
        return category.icon
    }

    var formattedFirstSeen: String {
        guard let firstSeen = firstSeen else { return "Unknown" }
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: firstSeen, relativeTo: Date())
    }

    var hasPremiumContent: Bool {
        return exampleUsage != nil || origin != nil || (relatedTerms?.isEmpty == false)
    }
}
