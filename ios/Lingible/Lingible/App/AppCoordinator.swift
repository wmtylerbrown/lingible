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

    // MARK: - Dependencies
    let authenticationService: AuthenticationServiceProtocol
    let userService: any UserServiceProtocol

    // MARK: - Published User Service Properties (for UI observation)
    var userProfile: UserProfileResponse? { userService.userProfile }
    var userUsage: UsageResponse? { userService.userUsage }
    var userServiceIsLoading: Bool { userService.isLoading }
    var lastProfileUpdate: Date? { userService.lastProfileUpdate }
    var lastUsageUpdate: Date? { userService.lastUsageUpdate }

    // MARK: - Private Properties
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization
    init(authenticationService: AuthenticationServiceProtocol, userService: any UserServiceProtocol) {
        self.authenticationService = authenticationService
        self.userService = userService
        setupBindings()
    }

    convenience init() {
        let authService = AuthenticationService()
        let userService = UserService(authenticationService: authService)
        self.init(authenticationService: authService, userService: userService)
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

    func authenticateUserWithApple() async throws -> AuthenticatedUser {
        let user = try await authenticationService.signInWithApple()

        // Update app state to authenticated after successful sign in
        currentState = .authenticated

        // Load user data after successful authentication
        await userService.loadUserData(forceRefresh: false)

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

        // Start auth check in background while showing splash
        let authTask = Task {
            return await authenticationService.checkAuthenticationStatus()
        }

        // Show splash for at least 3 seconds for good UX
        try? await Task.sleep(for: .seconds(3))

        // Get auth result (should be ready by now)
        let isAuthenticated = await authTask.value

        // Move directly to appropriate state (no intermediate loading)
        currentState = isAuthenticated ? .authenticated : .unauthenticated
        isLoading = false

        // Load user data after successful authentication
        if isAuthenticated {
            await userService.loadUserData(forceRefresh: false)
        }
    }
}

// MARK: - App State
enum AppState {
    case splash
    case unauthenticated
    case authenticated
}
