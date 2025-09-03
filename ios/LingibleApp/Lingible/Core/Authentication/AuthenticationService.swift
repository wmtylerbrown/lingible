import Foundation
import Combine
import Amplify
import AWSCognitoAuthPlugin
import AuthenticationServices

// MARK: - Authentication Service Protocol
protocol AuthenticationServiceProtocol {
    var isAuthenticated: AnyPublisher<Bool, Never> { get }
    var currentUser: AnyPublisher<AuthenticatedUser?, Never> { get }

    func checkAuthenticationStatus() async -> Bool
    func signInWithApple() async throws -> AuthenticatedUser
    func signOut() async throws
}

// MARK: - Authentication Service Implementation
@MainActor
final class AuthenticationService: NSObject, ObservableObject, AuthenticationServiceProtocol {

    // MARK: - Published Properties
    @Published private var _isAuthenticated = false
    @Published private var _currentUser: AuthenticatedUser?

    // MARK: - Public Publishers
    var isAuthenticated: AnyPublisher<Bool, Never> {
        $_isAuthenticated.eraseToAnyPublisher()
    }

    var currentUser: AnyPublisher<AuthenticatedUser?, Never> {
        $_currentUser.eraseToAnyPublisher()
    }

    // MARK: - Dependencies
    private let keychainStorage: KeychainStorageProtocol

    // MARK: - Initialization
    init(keychainStorage: KeychainStorageProtocol = KeychainStorage()) {
        self.keychainStorage = keychainStorage
        super.init()
    }

    // MARK: - Public Methods
    func checkAuthenticationStatus() async -> Bool {
        do {
            let session = try await Amplify.Auth.fetchAuthSession()

            if session.isSignedIn {
                // Get user attributes
                let user = try await Amplify.Auth.getCurrentUser()
                let userAttributes = try await Amplify.Auth.fetchUserAttributes()

                // Create authenticated user
                let authenticatedUser = AuthenticatedUser(
                    id: user.userId,
                    username: user.username,
                    email: extractEmail(from: userAttributes),
                    authSession: session
                )

                _currentUser = authenticatedUser
                _isAuthenticated = true

                return true
            } else {
                _currentUser = nil
                _isAuthenticated = false
                return false
            }
        } catch {
            print("❌ Error checking authentication status: \(error)")
            _currentUser = nil
            _isAuthenticated = false
            return false
        }
    }

    func signInWithApple() async throws -> AuthenticatedUser {
        do {
            // Perform Apple Sign In with Amplify
            let signInResult = try await Amplify.Auth.signInWithWebUI(
                for: .apple,
                presentationAnchor: await UIApplication.shared.windows.first
            )

            if signInResult.isSignedIn {
                // Get user information
                let user = try await Amplify.Auth.getCurrentUser()
                let session = try await Amplify.Auth.fetchAuthSession()
                let userAttributes = try await Amplify.Auth.fetchUserAttributes()

                let authenticatedUser = AuthenticatedUser(
                    id: user.userId,
                    username: user.username,
                    email: extractEmail(from: userAttributes),
                    authSession: session
                )

                _currentUser = authenticatedUser
                _isAuthenticated = true

                return authenticatedUser
            } else {
                throw AuthenticationError.signInFailed("Apple Sign In was not completed")
            }
        } catch {
            print("❌ Apple Sign In failed: \(error)")
            throw AuthenticationError.signInFailed(error.localizedDescription)
        }
    }

    func signOut() async throws {
        do {
            _ = try await Amplify.Auth.signOut()

            // Clear local state
            _currentUser = nil
            _isAuthenticated = false

            // Clear any stored tokens/data
            keychainStorage.clearAll()

        } catch {
            print("❌ Sign out failed: \(error)")
            throw AuthenticationError.signOutFailed(error.localizedDescription)
        }
    }

    // MARK: - Private Methods
    private func extractEmail(from attributes: [AuthUserAttribute]) -> String? {
        return attributes.first { $0.key == .email }?.value
    }
}

// MARK: - Authenticated User Model
struct AuthenticatedUser {
    let id: String
    let username: String
    let email: String?
    let authSession: AuthSession

    var accessToken: String? {
        guard let cognitoTokens = authSession as? AuthCognitoTokensProvider else {
            return nil
        }
        do {
            return try cognitoTokens.getCognitoTokens().get().accessToken
        } catch {
            print("❌ Error getting access token: \(error)")
            return nil
        }
    }
}

// MARK: - Authentication Errors
enum AuthenticationError: LocalizedError {
    case signInFailed(String)
    case signOutFailed(String)
    case invalidCredentials
    case networkError

    var errorDescription: String? {
        switch self {
        case .signInFailed(let message):
            return "Sign in failed: \(message)"
        case .signOutFailed(let message):
            return "Sign out failed: \(message)"
        case .invalidCredentials:
            return "Invalid credentials"
        case .networkError:
            return "Network error occurred"
        }
    }
}
