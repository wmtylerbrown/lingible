import SwiftUI
import AuthenticationServices

struct AuthenticationView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @StateObject private var authService = AuthenticationService()
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var isSigningIn = false

    var body: some View {
        ZStack {
            // Background
            Color.lingibleBackground
                .ignoresSafeArea()

            VStack(spacing: 40) {
                Spacer()

                // Logo and branding
                VStack(spacing: 20) {
                    Image("LingibleLogo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 80, height: 80)
                        .fadeInAnimation(delay: 0.2)

                    Image("WordmarkMedium")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(height: 40)
                        .fadeInAnimation(delay: 0.4)

                    Text("Bridge the gap between generations")
                        .font(.subheadline)
                        .foregroundColor(.lingibleSecondary)
                        .multilineTextAlignment(.center)
                        .fadeInAnimation(delay: 0.6)
                }

                Spacer()

                // Authentication options
                VStack(spacing: 20) {
                    // Apple Sign In Button
                    SignInWithAppleButton(
                        onRequest: { request in
                            request.requestedScopes = [.fullName, .email]
                        },
                        onCompletion: handleAppleSignIn
                    )
                    .signInWithAppleButtonStyle(.black)
                    .frame(height: 55)
                    .cornerRadius(12)
                    .disabled(isSigningIn)
                    .fadeInAnimation(delay: 0.8)

                    // Terms and Privacy
                    VStack(spacing: 8) {
                        Text("By signing in, you agree to our")
                            .font(.caption)
                            .foregroundColor(.lingibleSecondary)

                        HStack(spacing: 8) {
                            Link("Terms of Service", destination: URL(string: "https://lingible.com/terms")!)
                                .font(.caption)
                                .foregroundColor(.lingiblePrimary)

                            Text("and")
                                .font(.caption)
                                .foregroundColor(.lingibleSecondary)

                            Link("Privacy Policy", destination: URL(string: "https://lingible.com/privacy")!)
                                .font(.caption)
                                .foregroundColor(.lingiblePrimary)
                        }
                    }
                    .fadeInAnimation(delay: 1.0)
                }
                .padding(.horizontal, 32)

                Spacer()
            }

            // Loading overlay
            if isSigningIn {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()

                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.2)
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))

                    Text("Signing you in...")
                        .font(.subheadline)
                        .foregroundColor(.white)
                }
                .padding(24)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(.ultraThinMaterial)
                )
                .fadeInAnimation()
            }
        }
        .alert("Sign In Error", isPresented: $showError) {
            Button("OK") { }
        } message: {
            Text(errorMessage)
        }
    }

    // MARK: - Apple Sign In Handler
    private func handleAppleSignIn(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(_):
            Task {
                await performAppleSignIn()
            }
        case .failure(let error):
            handleSignInError(error)
        }
    }

    @MainActor
    private func performAppleSignIn() async {
        isSigningIn = true

        do {
            _ = try await authService.signInWithApple()
            // AppCoordinator will handle the state change through the authentication service
        } catch {
            handleSignInError(error)
        }

        isSigningIn = false
    }

    private func handleSignInError(_ error: Error) {
        errorMessage = error.localizedDescription
        showError = true
        isSigningIn = false
    }
}

#Preview {
    AuthenticationView()
        .environmentObject(AppCoordinator())
}
