import SwiftUI
import Combine
import LingibleAPI

/// App state coordinator following clean architecture principles
@MainActor
final class AppCoordinator: ObservableObject {

    // MARK: - Published Properties
    @Published var currentState: AppState = .splash
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var isUserDataLoaded = false

    // MARK: - Dependencies
    let authenticationService: AuthenticationServiceProtocol
    let userService: any UserServiceProtocol
    let adManager: AdManager
    let attManager: AppTrackingTransparencyManager

    // MARK: - Published User Service Properties (for UI observation)
    var userProfile: UserProfileResponse? { userService.userProfile }
    var userUsage: UsageResponse? { userService.userUsage }
    var userServiceIsLoading: Bool { userService.isLoading }
    var lastProfileUpdate: Date? { userService.lastProfileUpdate }
    var lastUsageUpdate: Date? { userService.lastUsageUpdate }

    // MARK: - Private Properties
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization
    init(authenticationService: AuthenticationServiceProtocol, userService: any UserServiceProtocol, attManager: AppTrackingTransparencyManager) {
        self.authenticationService = authenticationService
        self.userService = userService
        self.attManager = attManager
        self.adManager = AdManager(userService: userService, attManager: attManager)
        setupBindings()
    }

    convenience init() {
        let authService = AuthenticationService()
        let userService = UserService(authenticationService: authService)
        let attManager = AppTrackingTransparencyManager()
        self.init(authenticationService: authService, userService: userService, attManager: attManager)
    }

    // MARK: - Public Methods
    func checkAuthenticationStatus() {
        Task {
            await authenticateUser()
        }
    }

    func signOut() {
        Task {
            do {
                try await authenticationService.signOut()
                currentState = .unauthenticated
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    /// Restore authenticated state (used when ad dismissal causes state issues)
    func restoreAuthenticatedState() {
        currentState = .authenticated
        print("🔄 AppCoordinator: Restored authenticated state")
    }

    func authenticateUserWithApple() async throws -> AuthenticatedUser {
        let user = try await authenticationService.signInWithApple()

        // Load user data before showing main UI
        print("🔄 AppCoordinator: Loading user data after Apple sign in...")
        await userService.loadUserData(forceRefresh: false)

        // Wait for user data to be loaded
        await waitForUserDataLoading()

        // Now show the main UI with all data loaded
        currentState = .authenticated
        isUserDataLoaded = true
        print("✅ AppCoordinator: User data loaded after Apple sign in, showing main UI")

        // Request ATT permission after successful authentication
        await requestATTPermission()

        return user
    }

    // MARK: - Private Methods
    private func setupBindings() {
        // Note: We're not using automatic auth state binding anymore
        // State is now manually managed in authenticateUser() method
        // This gives us full control over the splash screen timing

        // Forward UserService changes to AppCoordinator for UI observation
        if let userService = userService as? UserService {
            userService.$userProfile
                .receive(on: DispatchQueue.main)
                .sink { [weak self] _ in
                    self?.objectWillChange.send()
                }
                .store(in: &cancellables)

            userService.$userUsage
                .receive(on: DispatchQueue.main)
                .sink { [weak self] _ in
                    self?.objectWillChange.send()
                }
                .store(in: &cancellables)

            userService.$isLoading
                .receive(on: DispatchQueue.main)
                .sink { [weak self] _ in
                    self?.objectWillChange.send()
                }
                .store(in: &cancellables)
        }
    }

        private func authenticateUser() async {
        // Always start with splash screen
        currentState = .splash
        isUserDataLoaded = false

        // Start auth check in background while showing splash
        let authTask = Task {
            return await authenticationService.checkAuthenticationStatus()
        }

        // Show splash for at least 3 seconds for good UX
        try? await Task.sleep(for: .seconds(3))

        // Get auth result (should be ready by now)
        let isAuthenticated = await authTask.value

        if isAuthenticated {
            // Load user data before showing main UI
            print("🔄 AppCoordinator: Loading user data before showing main UI...")
            await userService.loadUserData(forceRefresh: false)

            // Wait for user data to be loaded
            await waitForUserDataLoading()

            // Now show the main UI with all data loaded
            currentState = .authenticated
            isUserDataLoaded = true
            print("✅ AppCoordinator: User data loaded, showing main UI")
        } else {
            // No user data needed for unauthenticated state
            currentState = .unauthenticated
            isUserDataLoaded = true
        }

        isLoading = false
    }

    private func waitForUserDataLoading() async {
        // Wait for user data to be loaded
        while userService.isLoading {
            try? await Task.sleep(for: .milliseconds(100))
        }

        // Additional small delay to ensure UI updates are processed
        try? await Task.sleep(for: .milliseconds(200))
    }

    private func requestATTPermission() async {
        // Only request ATT permission if it hasn't been determined yet
        if attManager.shouldShowPermissionRequest {
            print("📱 AppCoordinator: Requesting ATT permission after authentication")
            await attManager.requestTrackingPermission()
        } else {
            print("📱 AppCoordinator: ATT permission already determined, skipping request")
        }
    }
}

// MARK: - App State
enum AppState {
    case splash
    case unauthenticated
    case authenticated
}
