import Foundation
import Combine
import Amplify
import AWSCognitoAuthPlugin
import AuthenticationServices

// MARK: - Authentication Service Protocol
@preconcurrency
protocol AuthenticationServiceProtocol {
    var isAuthenticated: AnyPublisher<Bool, Never> { get }
    var currentUser: AnyPublisher<AuthenticatedUser?, Never> { get }

    func checkAuthenticationStatus() async -> Bool
    func signInWithApple() async throws -> AuthenticatedUser
    func signOut() async throws
    func getCurrentUserValue() -> AuthenticatedUser?

    /// Get the current JWT access token for API calls
    func getAuthToken() async throws -> String

    /// Check if the current auth token is valid
    func isAuthTokenValid() async -> Bool
}

// MARK: - Authentication Service Implementation
@MainActor
@preconcurrency
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
    private let authTokenProvider: AuthTokenProvider

    // MARK: - Initialization
    init(keychainStorage: KeychainStorageProtocol = KeychainStorage(),
         authTokenProvider: AuthTokenProvider = AmplifyAuthTokenProvider()) {
        self.keychainStorage = keychainStorage
        self.authTokenProvider = authTokenProvider
        super.init()
    }

    // MARK: - Public Methods
    func checkAuthenticationStatus() async -> Bool {
        do {
            let session = try await Amplify.Auth.fetchAuthSession()

            if session.isSignedIn {
                // Get basic user info first
                let user = try await Amplify.Auth.getCurrentUser()

                // Try to get user attributes, but handle gracefully if we don't have permission
                var userEmail: String? = nil
                do {
                    let userAttributes = try await Amplify.Auth.fetchUserAttributes()
                    userEmail = extractEmail(from: userAttributes)
                } catch {
                    print("⚠️ Could not fetch user attributes during status check: \(error)")
                    // Continue without email for now
                }

                // Create authenticated user
                let authenticatedUser = AuthenticatedUser(
                    id: user.userId,
                    username: user.username,
                    email: userEmail,
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
        print("🍎 Starting Apple Sign In with Amplify Gen 2...")

        do {
            // Check if user is already signed in
            print("🔍 Checking if user is already signed in...")
            let currentSession = try await Amplify.Auth.fetchAuthSession()
            if currentSession.isSignedIn {
                print("✅ User is already signed in, fetching current user...")
                let user = try await fetchCurrentUser()
                print("✅ Current user fetched successfully")
                return user
            }

            // Check if Amplify is configured
            print("🔍 Checking Amplify configuration status...")
            do {
                let session = try await Amplify.Auth.fetchAuthSession()
                print("✅ Amplify Auth is accessible and configured")
                print("🔍 Session type: \(type(of: session))")
            } catch {
                print("⚠️ Amplify Auth configuration issue: \(error)")
            }

            // Add a small delay to ensure window hierarchy is fully established
            print("⏳ Waiting for window hierarchy to be fully established...")
            try await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds

            // Use Amplify's built-in Apple Sign In
            print("🔧 Calling Amplify.Auth.signInWithWebUI for Apple...")

            // Get the proper presentation anchor - use a more reliable method
            print("🔍 Debugging window hierarchy...")
            print("  - Connected scenes count: \(UIApplication.shared.connectedScenes.count)")
            for (index, scene) in UIApplication.shared.connectedScenes.enumerated() {
                print("  - Scene \(index): \(type(of: scene)), activation state: \(scene.activationState.rawValue)")
                if let windowScene = scene as? UIWindowScene {
                    print("    - Windows count: \(windowScene.windows.count)")
                    for (windowIndex, window) in windowScene.windows.enumerated() {
                        print("    - Window \(windowIndex): isKeyWindow=\(window.isKeyWindow), isHidden=\(window.isHidden), frame=\(window.frame)")
                    }
                }
            }

            let presentationAnchor: UIWindow
            if let windowScene = UIApplication.shared.connectedScenes
                .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene,
               let keyWindow = windowScene.windows.first(where: { $0.isKeyWindow && !$0.isHidden }) {
                presentationAnchor = keyWindow
                print("🔧 Using key window as presentation anchor: \(keyWindow)")
            } else if let windowScene = UIApplication.shared.connectedScenes
                .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene,
                      let firstVisibleWindow = windowScene.windows.first(where: { !$0.isHidden }) {
                presentationAnchor = firstVisibleWindow
                print("🔧 Using first visible window as presentation anchor: \(firstVisibleWindow)")
            } else if let firstWindowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
                      let firstWindow = firstWindowScene.windows.first(where: { !$0.isHidden }) {
                presentationAnchor = firstWindow
                print("🔧 Using first available visible window as presentation anchor: \(firstWindow)")
            } else {
                // Fallback: create a temporary window if needed
                let tempWindow = UIWindow(frame: UIScreen.main.bounds)
                tempWindow.windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene
                presentationAnchor = tempWindow
                print("🔧 Using temporary window as presentation anchor")
            }

            let signInResult = try await Amplify.Auth.signInWithWebUI(
                for: .apple,
                presentationAnchor: presentationAnchor
            )

            print("✅ Apple Sign In completed, checking result...")
            print("🔍 Sign in result: \(signInResult)")
            print("🔍 Is signed in: \(signInResult.isSignedIn)")

            if signInResult.isSignedIn {
                print("✅ User is signed in, fetching user details...")
                let user = try await fetchCurrentUser()
                print("✅ User details fetched successfully")
                return user
            } else {
                print("❌ Sign in result indicates user is not signed in")
                throw AuthenticationError.signInFailed("Apple Sign In was not completed")
            }

        } catch {
            print("❌ Apple Sign In failed: \(error)")
            print("🔍 Error details:")
            print("  - Error type: \(type(of: error))")
            print("  - Error description: \(error.localizedDescription)")
            if let nsError = error as NSError? {
                print("  - Error domain: \(nsError.domain)")
                print("  - Error code: \(nsError.code)")
                print("  - User info: \(nsError.userInfo)")
            }

            // Additional error context for Amplify errors
            if let amplifyError = error as? AuthError {
                print("🔍 Amplify AuthError details:")
                print("  - Error type: \(amplifyError)")
                print("  - Recovery suggestion: \(amplifyError.recoverySuggestion ?? "None")")
            }

            throw AuthenticationError.signInFailed(error.localizedDescription)
        }
    }

    func signOut() async throws {
        // Amplify.Auth.signOut() doesn't throw, so we don't need a do-catch block
        _ = await Amplify.Auth.signOut()

        // Clear local state
        _currentUser = nil
        _isAuthenticated = false

        // Clear any stored tokens/data
        keychainStorage.clearAll()
    }

    func getCurrentUserValue() -> AuthenticatedUser? {
        return _currentUser
    }

    func getAuthToken() async throws -> String {
        return try await authTokenProvider.getAuthToken()
    }

    func isAuthTokenValid() async -> Bool {
        return await authTokenProvider.isTokenValid()
    }

    // MARK: - Private Methods
    private func extractEmail(from attributes: [AuthUserAttribute]) -> String? {
        return attributes.first { $0.key == .email }?.value
    }

    private func fetchCurrentUser() async throws -> AuthenticatedUser {
        // Get user information
        let user = try await Amplify.Auth.getCurrentUser()
        print("👤 Current user: \(user.userId)")

        let session = try await Amplify.Auth.fetchAuthSession()
        print("🔑 Auth session fetched")

        // Try to fetch user attributes, but handle the case where we don't have permission
        var userEmail: String? = nil
        do {
            let userAttributes = try await Amplify.Auth.fetchUserAttributes()
            print("📋 User attributes: \(userAttributes.count) attributes")
            userEmail = extractEmail(from: userAttributes)
        } catch {
            print("⚠️ Could not fetch user attributes: \(error)")
            print("🔍 This is expected for new users or when access token lacks required scopes")
            // Continue without attributes for now
        }

        let authenticatedUser = AuthenticatedUser(
            id: user.userId,
            username: user.username,
            email: userEmail,
            authSession: session
        )

        _currentUser = authenticatedUser
        _isAuthenticated = true

        print("✅ Authentication completed successfully")
        return authenticatedUser
    }
}

// MARK: - Authenticated User Model
struct AuthenticatedUser {
    let id: String
    let username: String
    let email: String?
    let authSession: AuthSession

    var accessToken: String? {
        // Extract the access token from the auth session
        // For now, we'll need to get this from the session when making API calls
        // Amplify handles token management internally
        return nil
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
