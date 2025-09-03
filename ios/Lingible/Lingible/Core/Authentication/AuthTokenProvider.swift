import Foundation
import Amplify

/// Protocol for providing authentication tokens to API calls
protocol AuthTokenProvider {
    /// Get the current JWT access token for API authentication
    /// - Returns: The JWT token string, or throws an error if unavailable
    func getAuthToken() async throws -> String

    /// Check if the current token is still valid
    /// - Returns: True if token exists and is not expired
    func isTokenValid() async -> Bool
}

/// Implementation of AuthTokenProvider using Amplify Gen 2
class AmplifyAuthTokenProvider: AuthTokenProvider {

    /// Get the current JWT access token from Amplify
    /// - Returns: The JWT token string
    /// - Throws: AuthTokenError if token cannot be extracted
    func getAuthToken() async throws -> String {
        print("🔑 AuthTokenProvider: Getting JWT token from Amplify Gen 2 session...")

        let session = try await Amplify.Auth.fetchAuthSession()
        print("🔑 AuthTokenProvider: Session type: \(type(of: session))")

        // Use reflection to inspect the session and find the userPoolTokensResult
        let mirror = Mirror(reflecting: session)
        for child in mirror.children {
            if let label = child.label {
                print("🔑 AuthTokenProvider: Property: \(label)")

                // The userPoolTokensResult contains the JWT tokens
                if label == "userPoolTokensResult" {
                    print("🔑 AuthTokenProvider: Found userPoolTokensResult, examining contents...")

                    // Use reflection to examine the Result type
                    let resultMirror = Mirror(reflecting: child.value)
                    for resultChild in resultMirror.children {
                        if let resultLabel = resultChild.label {
                            print("🔑 AuthTokenProvider: Result property: \(resultLabel)")

                            // Look for the success case that contains the tokens
                            if resultLabel == "success" {
                                print("🔑 AuthTokenProvider: Found success case, examining tokens...")

                                // The success case contains a dictionary with the tokens
                                let tokensMirror = Mirror(reflecting: resultChild.value)
                                for tokenChild in tokensMirror.children {
                                    if let tokenLabel = tokenChild.label {
                                        print("🔑 AuthTokenProvider: Token property: \(tokenLabel)")

                                        // Look for the accessToken
                                        if tokenLabel == "accessToken" {
                                            if let token = tokenChild.value as? String {
                                                print("✅ AuthTokenProvider: Found JWT token: \(String(token.prefix(20)))...")

                                                // Validate the token format
                                                let tokenParts = token.components(separatedBy: ".")
                                                guard tokenParts.count == 3 else {
                                                    throw AuthTokenError.invalidTokenFormat("Token should have 3 parts (header.payload.signature), found \(tokenParts.count)")
                                                }

                                                return token
                                            }
                                        }
                                    }
                                }
                                break
                            }
                        }
                    }
                    break
                }
            }
        }

        throw AuthTokenError.tokenNotFound("Could not extract JWT token from session. Available properties: \(mirror.children.map { $0.label ?? "nil" }.joined(separator: ", "))")
    }

    /// Check if the current token is still valid
    /// - Returns: True if token exists and is not expired
    func isTokenValid() async -> Bool {
        do {
            let _ = try await getAuthToken()
            return true
        } catch {
            return false
        }
    }
}

/// Errors that can occur when getting authentication tokens
enum AuthTokenError: LocalizedError {
    case tokenNotFound(String)
    case invalidTokenFormat(String)
    case sessionExpired

    var errorDescription: String? {
        switch self {
        case .tokenNotFound(let details):
            return "Authentication token not found: \(details)"
        case .invalidTokenFormat(let details):
            return "Invalid token format: \(details)"
        case .sessionExpired:
            return "Authentication session has expired. Please sign in again."
        }
    }
}
