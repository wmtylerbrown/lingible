import SwiftUI
import AppTrackingTransparency

// MARK: - App Tracking Transparency Privacy View
struct ATTPrivacyView: View {

    // MARK: - Properties
    @ObservedObject var attManager: AppTrackingTransparencyManager
    @State private var isRequesting = false
    @Environment(\.dismiss) private var dismiss

    // MARK: - Body
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {

                // Header
                VStack(spacing: 16) {
                    Image(systemName: "hand.raised.fill")
                        .font(.system(size: 60))
                        .foregroundColor(.blue)

                    Text("Privacy & Ads")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Help keep Lingible free")
                        .font(.title2)
                        .foregroundColor(.secondary)
                }
                .padding(.top, 20)

                // Content
                VStack(spacing: 20) {

                    // Benefits
                    VStack(alignment: .leading, spacing: 12) {
                        BenefitRow(
                            icon: "target",
                            title: "Personalized Ads",
                            description: "See ads that match your interests"
                        )

                        BenefitRow(
                            icon: "gift",
                            title: "Free App",
                            description: "Keep the app free for everyone"
                        )

                        BenefitRow(
                            icon: "shield.checkered",
                            title: "Privacy Protected",
                            description: "You control your data and can change this anytime"
                        )
                    }
                    .padding(.horizontal, 20)

                    // Message
                    Text(attManager.permissionRequestMessage)
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 20)
                }

                Spacer()

                // Action Buttons
                VStack(spacing: 12) {

                    // Allow Button
                    Button(action: {
                        requestPermission()
                    }) {
                        HStack {
                            if isRequesting {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                    .scaleEffect(0.8)
                            } else {
                                Image(systemName: "checkmark.circle.fill")
                            }

                            Text("Allow Personalized Ads")
                                .fontWeight(.semibold)
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(Color.blue)
                        .cornerRadius(12)
                    }
                    .disabled(isRequesting)

                    // Ask App Not to Track Button
                    Button(action: {
                        requestPermission()
                    }) {
                        HStack {
                            Image(systemName: "xmark.circle")
                            Text("Ask App Not to Track")
                                .fontWeight(.medium)
                        }
                        .foregroundColor(.primary)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(Color.gray.opacity(0.1))
                        .cornerRadius(12)
                    }
                    .disabled(isRequesting)

                    // Learn More Button
                    Button(action: {
                        // Open privacy settings or help page
                        openPrivacySettings()
                    }) {
                        Text("Learn More About Privacy")
                            .font(.caption)
                            .foregroundColor(.blue)
                    }
                    .padding(.top, 8)
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 20)
            }
            .navigationBarHidden(true)
        }
    }

    // MARK: - Private Methods

    private func requestPermission() {
        isRequesting = true

        Task {
            await attManager.requestTrackingPermission()

            await MainActor.run {
                isRequesting = false
                dismiss()
            }
        }
    }

    private func openPrivacySettings() {
        if let url = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(url)
        }
    }
}

// MARK: - Benefit Row Component
struct BenefitRow: View {
    let icon: String
    let title: String
    let description: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.blue)
                .frame(width: 24, height: 24)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                    .fontWeight(.semibold)

                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
    }
}

// MARK: - Preview
struct ATTPrivacyView_Previews: PreviewProvider {
    static var previews: some View {
        ATTPrivacyView(attManager: AppTrackingTransparencyManager())
    }
}
