import SwiftUI
import Combine

/// App state coordinator following clean architecture principles
@MainActor
final class AppCoordinator: ObservableObject {

    // MARK: - Published Properties
    @Published var currentState: AppState = .splash
    @Published var isLoading = false
    @Published var errorMessage: String?

    // MARK: - Dependencies
    let authenticationService: AuthenticationServiceProtocol

    // MARK: - Private Properties
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization
    init(authenticationService: AuthenticationServiceProtocol) {
        self.authenticationService = authenticationService
        setupBindings()
    }

    convenience init() {
        self.init(authenticationService: AuthenticationService())
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
        return try await authenticationService.signInWithApple()
    }

    // MARK: - Private Methods
    private func setupBindings() {
        // Listen to authentication state changes
        authenticationService.isAuthenticated
            .receive(on: DispatchQueue.main)
            .sink { [weak self] isAuthenticated in
                self?.currentState = isAuthenticated ? .authenticated : .unauthenticated
            }
            .store(in: &cancellables)
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
    }
}

// MARK: - App State
enum AppState {
    case splash
    case unauthenticated
    case authenticated
}
