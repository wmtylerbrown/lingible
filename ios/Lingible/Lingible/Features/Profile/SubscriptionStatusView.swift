import SwiftUI
import StoreKit
import LingibleAPI

struct SubscriptionStatusView: View {
    @StateObject private var subscriptionManager = SubscriptionManager()
    let userUsage: UsageResponse?
    var onManageAction: (() -> Void)?
    var onUpgradeAction: (() -> Void)?

    var body: some View {
        VStack(spacing: 16) {
            if userUsage?.tier == .premium {
                // Premium user status
                HStack(spacing: 12) {
                    Image(systemName: "crown.fill")
                        .font(.title2)
                        .foregroundColor(.yellow)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Premium Active")
                            .font(.headline)
                            .fontWeight(.semibold)
                        Text("100 daily translations")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    Button("Manage") {
                        onManageAction?()
                    }
                    .font(.caption)
                    .foregroundColor(.lingiblePrimary)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.yellow.opacity(0.1))
                .cornerRadius(12)
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Premium subscription active")
                .accessibilityHint("100 daily translations available")
            } else {
                // Free user status
                HStack(spacing: 12) {
                    Image(systemName: "star")
                        .font(.title2)
                        .foregroundColor(.lingiblePrimary)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Free Plan")
                            .font(.headline)
                            .fontWeight(.semibold)
                        Text("Limited translations")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    Button("Upgrade") {
                        onUpgradeAction?()
                    }
                    .font(.caption)
                    .foregroundColor(.lingiblePrimary)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.lingiblePrimary.opacity(0.1))
                .cornerRadius(12)
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Free plan")
                .accessibilityHint("Limited translations available")
            }
        }
    }
}

#Preview {
    SubscriptionStatusView(userUsage: nil)
        .padding()
}
