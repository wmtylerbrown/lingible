import SwiftUI
import StoreKit
import LingibleAPI

struct UpgradePromptView: View {
    let translationCount: Int?
    let onUpgrade: () -> Void
    let onDismiss: () -> Void
    let userUsage: UsageResponse?

    @Environment(\.dismiss) private var dismiss
    @State private var subscriptionManager: SubscriptionManager?
    @State private var isPurchasing = false
    @State private var showingSuccessAlert = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Header with usage info
                    if let count = translationCount, count > 0 {
                        VStack(spacing: 8) {
                            Text("You've used \(count) translations today")
                                .font(.headline)
                                .foregroundColor(.primary)

                            Text("Time to level up your GenZ game! 🚀")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        .padding(.top, 20)
                    }

                    // Benefits list - based on actual app limits
                    VStack(alignment: .leading, spacing: 12) {
                        benefitRow(icon: "arrow.up.circle", title: "10x More Daily Translations", description: "100 GenZ translations per day (vs 10 free)")
                        benefitRow(icon: "textformat.size", title: "Bigger Text Slabs", description: "Drop those longer GenZ phrases up to 100 characters (vs 50 free)")
                        benefitRow(icon: "clock.arrow.circlepath", title: "Translation Memory Bank", description: "Keep track of all your fire translations for 30 days")
                        benefitRow(icon: "xmark.rectangle", title: "No More Ads", description: "Clean experience without those annoying interruptions")
                    }
                    .padding(.horizontal, 20)

                    // Subscribe Button - custom purchase flow
                    VStack(spacing: 16) {
                        Button(action: {
                            Task {
                                await purchaseSubscription()
                            }
                        }) {
                            VStack(spacing: 8) {
                                if isPurchasing {
                                    HStack(spacing: 8) {
                                        ProgressView()
                                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                            .scaleEffect(0.8)
                                        Text("Processing...")
                                            .font(.title2)
                                            .fontWeight(.bold)
                                            .foregroundColor(.white)
                                    }
                                } else {
                                Text("Join the Premium Squad")
                                    .font(.title2)
                                    .fontWeight(.bold)
                                    .foregroundColor(.white)
                                }

                                Text("$2.99/month")
                                    .font(.headline)
                                    .foregroundColor(.white.opacity(0.9))
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(
                                LinearGradient(
                                    colors: [.lingiblePrimary, .lingiblePrimary.opacity(0.8)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .cornerRadius(12)
                            .shadow(color: .lingiblePrimary.opacity(0.3), radius: 8, x: 0, y: 4)
                        }
                        .disabled(isPurchasing)

                        Text("Level up your GenZ translation game today")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal, 20)
                    .onAppear {
                        // No automatic subscription loading - only when user actually purchases
                        print("🛒 UpgradePromptView appeared - no automatic subscription loading")
                    }
                }
                .padding(.bottom, 20)
            }
            .navigationTitle("Go Premium")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Close") {
                        dismiss()
                    }
                    .foregroundColor(.secondary)
                }
            }
            .alert("Upgrade Successful!", isPresented: $showingSuccessAlert) {
                Button("Continue") {
                    // Close both the upgrade prompt and trigger app refresh
                    onUpgrade()
                    dismiss()
                }
            } message: {
                Text("Welcome to the premium squad! 🚀\n\nYou can now translate 100 GenZ slang phrases per day instead of just 10. Let's gooo!")
            }
        }
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

    // MARK: - Purchase Flow
    private func purchaseSubscription() async {
        // Only create SubscriptionManager when actually purchasing
        if subscriptionManager == nil {
            subscriptionManager = SubscriptionManager(onUserDataRefresh: {
                // This callback will refresh the main UserService instance
                // which is what the AdManager is observing
                await self.refreshUserData()
            })
        }

        guard let manager = subscriptionManager else {
            print("❌ Failed to create SubscriptionManager")
            return
        }

        // Load products first
        await manager.loadProducts()

        guard let product = manager.products.first else {
            print("❌ No products available for purchase")
            return
        }

        print("🛒 Starting purchase for: \(product.displayName)")
        isPurchasing = true

        let success = await manager.purchase(product)

        await MainActor.run {
            isPurchasing = false

            if success {
                print("✅ Purchase successful - showing success alert")
                showingSuccessAlert = true

                // Force refresh user data to ensure backend sync is reflected
                Task {
                    await refreshUserData()

                    // Add a small delay to ensure the backend sync has completed
                    try? await Task.sleep(nanoseconds: 1_000_000_000) // 1 second

                    // Force another refresh to ensure we get the latest tier status
                    await refreshUserData()
                }
            } else {
                print("❌ Purchase failed or was cancelled")
            }
        }
    }

    // MARK: - User Data Refresh
    private func refreshUserData() async {
        print("🔄 Force refreshing user data after purchase...")
        // This will be handled by the onUpgrade callback in ProfileView
        // which calls appCoordinator.userService.refreshUserData()
        onUpgrade()
    }

    // MARK: - Subscription State Management
    private func refreshSubscriptionState() async {
        print("🔄 Forcing subscription state refresh...")

        // Clear any cached state by forcing StoreKit to refresh
        do {
            try await AppStore.sync()
            print("✅ AppStore sync completed")
        } catch {
            print("❌ AppStore sync failed: \(error)")
        }

        // Print current subscription state for debugging
        print("📊 Current subscription state:")
        print("📊 Group ID: \(AppConfiguration.subscriptionGroupID)")
        print("📊 Product ID: \(AppConfiguration.subscriptionProductID)")

        // Check current entitlements
        var hasActiveSubscription = false
        var activeTransactions: [String] = []

        for await result in Transaction.currentEntitlements {
            do {
                let transaction = try checkVerified(result)
                activeTransactions.append(transaction.productID)
                print("📊 Active transaction: \(transaction.productID)")
                print("📊 Expiration: \(transaction.expirationDate?.description ?? "none")")
                print("📊 Purchase Date: \(transaction.purchaseDate.description)")
                print("📊 Revocation Date: \(transaction.revocationDate?.description ?? "none")")

                if transaction.productID == AppConfiguration.subscriptionProductID {
                    hasActiveSubscription = true
                }
            } catch {
                print("❌ Transaction verification failed: \(error)")
            }
        }

        print("📊 Total active transactions: \(activeTransactions.count)")
        print("📊 Has active subscription: \(hasActiveSubscription)")

        // If we have unexpected active transactions, try to clear them
        if hasActiveSubscription && activeTransactions.isEmpty == false {
            print("⚠️ Found unexpected active transactions - this might be causing the UI issue")
            print("⚠️ Consider signing out and back into App Store or resetting simulator")
        }
    }

    // MARK: - Verification Helper
    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified:
            throw StoreError.failedVerification
        case .verified(let safe):
            return safe
        }
    }

    // MARK: - Store Error
    private enum StoreError: Error {
        case failedVerification
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
