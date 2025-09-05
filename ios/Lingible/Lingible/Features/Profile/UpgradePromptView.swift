import SwiftUI
import LingibleAPI

struct UpgradePromptView: View {
    let translationCount: Int?
    let onUpgrade: () -> Void
    let onDismiss: () -> Void
    let userUsage: UsageResponse?

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                // Header with celebration
                VStack(spacing: 16) {
                    ZStack {
                        Circle()
                            .fill(Color.lingiblePrimary.opacity(0.1))
                            .frame(width: 100, height: 100)

                        Image(systemName: "star.circle.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.yellow)
                    }

                    if let count = translationCount {
                        Text("You've made \(count) translations!")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .multilineTextAlignment(.center)
                    } else {
                        Text("Upgrade to Premium")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding(.top, 20)

                // Benefits list
                VStack(alignment: .leading, spacing: 12) {
                    benefitRow(icon: "number.circle", title: "\(premiumDailyLimit) Daily Translations", description: "\(premiumMultiplier)x more translations than free plan")
                    benefitRow(icon: "textformat.size", title: "Longer Text Support", description: "Translate up to \(premiumMaxLength) characters")
                    benefitRow(icon: "clock.arrow.circlepath", title: "Translation History", description: "Access your translation history for 30 days")
                }
                .padding(.horizontal, 20)

                Spacer()

                // Action buttons
                VStack(spacing: 16) {
                    Button(action: onUpgrade) {
                        HStack {
                            Image(systemName: "star.fill")
                            Text("Upgrade to Premium")
                                .fontWeight(.semibold)
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color.lingiblePrimary)
                        .cornerRadius(12)
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
            .gesture(
                DragGesture()
                    .onEnded { value in
                        if value.translation.height > 100 {
                            dismiss()
                        }
                    }
            )
        }
    }

    // MARK: - Computed Properties
    private var premiumDailyLimit: Int {
        userUsage?.premiumDailyLimit ?? 100
    }

    private var premiumMaxLength: Int {
        userUsage?.premiumTierMaxLength ?? 100
    }

    private var freeDailyLimit: Int {
        userUsage?.freeDailyLimit ?? 10
    }

    private var premiumMultiplier: Int {
        let premium = premiumDailyLimit
        let free = freeDailyLimit
        return premium / free
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

#Preview {
    UpgradePromptView(
        translationCount: 3,
        onUpgrade: { print("Upgrade tapped") },
        onDismiss: { print("Dismiss tapped") },
        userUsage: nil
    )
}
