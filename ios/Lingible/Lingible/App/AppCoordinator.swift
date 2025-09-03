import SwiftUI
import Combine

/// App state coordinator following clean architecture principles
@MainActor
final class AppCoordinator: ObservableObject {

    // MARK: - Published Properties
    @Published var currentState: AppState = .loading
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
        isLoading = true

        // Show splash screen for at least 2 seconds for good UX
        let splashTask = Task {
            try await Task.sleep(for: .seconds(2))
        }

        let authTask = Task {
            return await authenticationService.checkAuthenticationStatus()
        }

        // Wait for both tasks to complete
        do {
            try await splashTask.value
            let isAuthenticated = await authTask.value

            currentState = isAuthenticated ? .authenticated : .unauthenticated
        } catch {
            currentState = .unauthenticated
            errorMessage = "Failed to check authentication status"
        }

        isLoading = false
    }
}

// MARK: - App State
enum AppState {
    case loading
    case unauthenticated
    case authenticated
}
