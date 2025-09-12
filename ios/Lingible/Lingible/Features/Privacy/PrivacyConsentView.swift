import SwiftUI
import SafariServices

// MARK: - Privacy Consent View
struct PrivacyConsentView: View {

    // MARK: - Properties
    @State private var showingPrivacyPolicy = false
    @State private var showingTermsOfService = false
    @State private var isProcessing = false

    let onConsentGiven: () -> Void
    let onConsentDenied: () -> Void

    // MARK: - Body
    var body: some View {
        NavigationView {
            VStack(spacing: 32) {

                // Header
                VStack(spacing: 20) {
                    Image(systemName: "hand.raised.fill")
                        .font(.system(size: 60))
                        .foregroundColor(.blue)

                    Text("Welcome to Lingible!")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("We need your consent to provide the best translation experience")
                        .font(.title3)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 20)
                }
                .padding(.top, 40)

                // Simple Consent Message
                VStack(spacing: 16) {
                    Text("By using Lingible, you agree to our:")
                        .font(.headline)
                        .foregroundColor(.primary)

                    VStack(spacing: 12) {
                        Button(action: { showingPrivacyPolicy = true }) {
                            HStack {
                                Image(systemName: "hand.raised")
                                    .foregroundColor(.blue)
                                Text("Privacy Policy")
                                    .foregroundColor(.blue)
                                    .fontWeight(.medium)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .foregroundColor(.blue)
                                    .font(.caption)
                            }
                            .padding()
                            .background(Color.blue.opacity(0.1))
                            .cornerRadius(12)
                        }

                        Button(action: { showingTermsOfService = true }) {
                            HStack {
                                Image(systemName: "doc.text")
                                    .foregroundColor(.blue)
                                Text("Terms of Service")
                                    .foregroundColor(.blue)
                                    .fontWeight(.medium)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .foregroundColor(.blue)
                                    .font(.caption)
                            }
                            .padding()
                            .background(Color.blue.opacity(0.1))
                            .cornerRadius(12)
                        }
                    }
                    .padding(.horizontal, 20)
                }

                // Data Collection Info
                VStack(spacing: 12) {
                    Text("What we collect:")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)

                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                                .font(.caption)
                            Text("Translation text (temporarily)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                                .font(.caption)
                            Text("Usage analytics (anonymous)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                                .font(.caption)
                            Text("Device info for ads (if you allow tracking)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding(.horizontal, 20)

                Spacer()

                // Action Buttons
                VStack(spacing: 16) {
                    Button(action: handleAgree) {
                        HStack {
                            if isProcessing {
                                ProgressView()
                                    .scaleEffect(0.8)
                                    .foregroundColor(.white)
                            } else {
                                Image(systemName: "checkmark.circle.fill")
                                    .font(.title2)
                            }

                            Text(isProcessing ? "Processing..." : "I Agree & Continue")
                                .font(.headline)
                                .fontWeight(.semibold)
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .cornerRadius(12)
                    }
                    .disabled(isProcessing)

                    Button(action: handleDeny) {
                        Text("I Don't Agree")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .disabled(isProcessing)
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 30)
            }
            .navigationTitle("Privacy Consent")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showingPrivacyPolicy) {
                SafariView(url: URL(string: AppConfiguration.privacyPolicyURL)!)
            }
            .sheet(isPresented: $showingTermsOfService) {
                SafariView(url: URL(string: AppConfiguration.termsOfServiceURL)!)
            }
        }
    }

    // MARK: - Actions
    private func handleAgree() {
        isProcessing = true

        // Store consent given
        UserDefaults.standard.set(true, forKey: "consent_given")
        UserDefaults.standard.synchronize()

        // Simulate processing time
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            isProcessing = false
            onConsentGiven()
        }
    }

    private func handleDeny() {
        onConsentDenied()
    }
}

// MARK: - Safari View
struct SafariView: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        return SFSafariViewController(url: url)
    }

    func updateUIViewController(_ uiViewController: SFSafariViewController, context: Context) {}
}
