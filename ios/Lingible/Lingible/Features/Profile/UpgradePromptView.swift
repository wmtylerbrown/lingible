import SwiftUI
import StoreKit
import LingibleAPI

struct UpgradePromptView: View {
    let translationCount: Int?
    let onUpgrade: () -> Void
    let onDismiss: () -> Void
    let userUsage: UsageResponse?

    @Environment(\.dismiss) private var dismiss
    @State private var showingManageSubscriptions = false

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Custom header with your branding
                VStack(spacing: 20) {
                    // Celebration header
                    VStack(spacing: 16) {
                        ZStack {
                            Circle()
                                .fill(Color.lingiblePrimary.opacity(0.1))
                                .frame(width: 100, height: 100)

                            Image(systemName: "star.circle.fill")
                                .font(.system(size: 60))
                                .foregroundColor(.yellow)
                        }

                        Text("Upgrade to Premium")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .multilineTextAlignment(.center)

                        if let count = translationCount, count > 0 {
                            Text("You've used \(count) translations today. Unlock 100 daily translations and premium features!")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 20)
                        } else {
                            Text("Unlock 100 daily translations and premium features")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                                .multilineTextAlignment(.center)
                        }
                    }
                    .padding(.top, 20)

                    // Benefits list
                    VStack(alignment: .leading, spacing: 12) {
                        benefitRow(icon: "infinity", title: "100 Daily Translations", description: "10x more than free tier")
                        benefitRow(icon: "textformat.size", title: "Longer Text Support", description: "Translate up to \(premiumMaxLength) characters")
                        benefitRow(icon: "clock.arrow.circlepath", title: "Translation History", description: "Access your translation history for 30 days")
                        benefitRow(icon: "xmark.rectangle", title: "Ad-Free Experience", description: "Remove all advertisements")
                    }
                    .padding(.horizontal, 20)
                }
                .padding(.bottom, 20)

                // Apple's native subscription view
                SubscriptionStoreView(groupID: "21482456")
                    .frame(height: 300)
                    .background(Color(.systemGroupedBackground))

                // Custom footer with manage subscriptions
                VStack(spacing: 16) {
                    Button(action: {
                        showingManageSubscriptions = true
                    }) {
                        Text("Manage Subscription")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.lingiblePrimary)
                    }

                    Button(action: onDismiss) {
                        Text("Continue with Free Plan")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.lingiblePrimary)
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 20)
            }
            .navigationTitle("Premium Upgrade")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Close") {
                        dismiss()
                    }
                    .foregroundColor(.secondary)
                }
            }
        }
        .sheet(isPresented: $showingManageSubscriptions) {
            NavigationView {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 16) {
                        Image(systemName: "creditcard.circle.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.lingiblePrimary)

                        Text("Manage Subscription")
                            .font(.title2)
                            .fontWeight(.semibold)

                        Text("To manage your subscription, billing, or payment methods, please visit the App Store.")
                            .font(.body)
                            .multilineTextAlignment(.center)
                            .foregroundColor(.secondary)
                            .padding(.horizontal)
                    }

                    // Action buttons
                    VStack(spacing: 12) {
                        Button(action: {
                            if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
                                UIApplication.shared.open(url)
                            }
                            showingManageSubscriptions = false
                        }) {
                            HStack {
                                Image(systemName: "external-link")
                                Text("Open App Store")
                            }
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(Color.lingiblePrimary)
                            .cornerRadius(12)
                        }

                        Button(action: {
                            showingManageSubscriptions = false
                        }) {
                            Text("Cancel")
                                .font(.headline)
                                .foregroundColor(.lingiblePrimary)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 16)
                                .background(Color(.systemGray6))
                                .cornerRadius(12)
                        }
                    }
                    .padding(.horizontal)

                    Spacer()
                }
                .padding()
                .navigationTitle("Subscription")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Button("Done") {
                            showingManageSubscriptions = false
                        }
                        .foregroundColor(.lingiblePrimary)
                    }
                }
            }
            .presentationDetents([.medium])
            .presentationDragIndicator(.visible)
        }
    }

    // MARK: - Computed Properties
    private var premiumMaxLength: Int {
        userUsage?.premiumTierMaxLength ?? 1000
    }

    // MARK: - Helper Views
    private func benefitRow(icon: String, title: String, description: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.lingiblePrimary)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
    }
}

#Preview("With Translation Count") {
    UpgradePromptView(
        translationCount: 10,
        onUpgrade: { },
        onDismiss: { },
        userUsage: nil
    )
}

#Preview("Without Translation Count") {
    UpgradePromptView(
        translationCount: nil,
        onUpgrade: { },
        onDismiss: { },
        userUsage: nil
    )
}
