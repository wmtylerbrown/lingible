import Foundation
import StoreKit
import SwiftUI
import LingibleAPI

/// Manages subscription purchases and status using StoreKit 2
@MainActor
class SubscriptionManager: ObservableObject {

    // MARK: - Published Properties
    @Published var products: [Product] = []
    @Published var purchasedSubscriptions: [Product] = []
    @Published var subscriptionStatus: SubscriptionStatus = .unknown
    @Published var isLoading = false
    @Published var errorMessage: String?

    // MARK: - Private Properties
    private let productIds: [String] = [AppConfiguration.subscriptionProductID]
    private var updateListenerTask: Task<Void, Error>? = nil
    private let onUserDataRefresh: (() async -> Void)?

    // Always use real StoreKit products (no development mode)

    // MARK: - Subscription Status
    enum SubscriptionStatus {
        case unknown
        case free
        case premium
        case expired
    }

    // MARK: - Initialization
    init(onUserDataRefresh: (() async -> Void)? = nil) {
        self.onUserDataRefresh = onUserDataRefresh

        // Start listening for transaction updates
        updateListenerTask = listenForTransactions()

        // Load products and check subscription status
        Task {
            await loadProducts()
            await updateSubscriptionStatus()
        }
    }

    deinit {
        updateListenerTask?.cancel()
    }

    // MARK: - Product Loading
    func loadProducts() async {
        do {
            isLoading = true
            errorMessage = nil

            print("🛒 Attempting to load products from App Store...")
            print("🛒 Product IDs: \(productIds)")
            print("🛒 Bundle ID: \(Bundle.main.bundleIdentifier ?? "unknown")")
            print("🛒 App Store Environment: \(Transaction.currentEntitlements)")

            // Check if we're in sandbox mode using AppTransaction
            do {
                let verificationResult = try await AppTransaction.shared
                let appTransaction = try checkVerified(verificationResult)
                print("🛒 App Transaction Environment: \(appTransaction.environment)")
                print("🛒 Sandbox Mode: \(appTransaction.environment == .sandbox)")
            } catch {
                print("🛒 Could not get AppTransaction: \(error)")
            }

            let storeProducts = try await Product.products(for: productIds)

            // Sort products by price (cheapest first)
            self.products = storeProducts.sorted { $0.price < $1.price }

            print("🛒 Loaded \(products.count) subscription products")
            for product in products {
                print("  - \(product.displayName): \(product.displayPrice)")
                print("  - Product ID: \(product.id)")
                print("  - Type: \(product.type)")
                print("  - Subscription Group: \(product.subscription?.subscriptionGroupID ?? "none")")
            }

            // Debug: Check if we're in simulator and StoreKit config should be available
            #if targetEnvironment(simulator)
            print("🛒 Running in iOS Simulator - StoreKit configuration should be available")
            #else
            print("🛒 Running on device - using real App Store products")
            #endif

            if products.isEmpty {
                print("❌ No products found - this could mean:")
                print("  1. Product doesn't exist in App Store Connect")
                print("  2. Product exists but isn't approved/available")
                print("  3. Bundle ID mismatch")
                print("  4. App not properly configured for In-App Purchases")
            }

        } catch {
            print("❌ Failed to load products: \(error)")
            errorMessage = "Failed to load subscription options. Please try again."
        }

        isLoading = false
    }


    // MARK: - Purchase Flow
    func purchase(_ product: Product) async -> Bool {
        do {
            isLoading = true
            errorMessage = nil

            print("🛒 Starting purchase for: \(product.displayName)")

            let result = try await product.purchase()

            switch result {
            case .success(let verification):
                let transaction = try checkVerified(verification)

                print("✅ Purchase successful: \(transaction.productID)")

                // Update subscription status
                await updateSubscriptionStatus()

                // Sync with backend - this is critical for the app to work properly
                let backendSyncSuccess = await syncSubscriptionWithBackend(transaction: transaction)

                if !backendSyncSuccess {
                    print("⚠️ Purchase succeeded but backend sync failed - user may need to refresh")
                    // Don't return false here - the purchase was successful, just the backend sync failed
                    // The user can refresh manually or the app can retry later
                }

                // Finish the transaction
                await transaction.finish()

                isLoading = false
                return true

            case .userCancelled:
                print("🚫 User cancelled purchase")
                errorMessage = "Purchase was cancelled"
                isLoading = false
                return false

            case .pending:
                print("⏳ Purchase pending approval")
                errorMessage = "Purchase is pending approval"
                isLoading = false
                return false

            @unknown default:
                print("❓ Unknown purchase result")
                errorMessage = "Unknown purchase result"
                isLoading = false
                return false
            }

        } catch {
            print("❌ Purchase failed: \(error)")
            errorMessage = "Purchase failed: \(error.localizedDescription)"
            isLoading = false
            return false
        }
    }

    // MARK: - Restore Purchases
    func restorePurchases() async -> Bool {
        do {
            isLoading = true
            errorMessage = nil

            print("🔄 Restoring purchases...")

            try await AppStore.sync()
            await updateSubscriptionStatus()

            if subscriptionStatus == .premium {
                print("✅ Purchases restored successfully")

                // Sync with backend for each active transaction
                await syncActiveTransactionsWithBackend()

                isLoading = false
                return true
            } else {
                print("ℹ️ No active subscriptions found")
                errorMessage = "No active subscriptions found"
                isLoading = false
                return false
            }

        } catch {
            print("❌ Failed to restore purchases: \(error)")
            errorMessage = "Failed to restore purchases: \(error.localizedDescription)"
            isLoading = false
            return false
        }
    }

    // MARK: - Backend Integration
    private func syncActiveTransactionsWithBackend() async {
        print("🔄 Syncing active transactions with backend...")

        // Get all active transactions and sync them with the backend
        for await result in Transaction.currentEntitlements {
            do {
                let transaction = try checkVerified(result)

                // Check if this is a subscription product
                if productIds.contains(transaction.productID) {
                    // Check if subscription is still active
                    if let expirationDate = transaction.expirationDate {
                        if expirationDate > Date() {
                            print("🔄 Syncing active subscription: \(transaction.productID)")
                            _ = await syncSubscriptionWithBackend(transaction: transaction)
                        }
                    } else {
                        // Non-consumable or lifetime subscription
                        print("🔄 Syncing lifetime subscription: \(transaction.productID)")
                        _ = await syncSubscriptionWithBackend(transaction: transaction)
                    }
                }
            } catch {
                print("❌ Failed to verify transaction during sync: \(error)")
            }
        }
    }

    func upgradeUserWithBackend(_ request: UserUpgradeRequest) async -> Bool {
        print("🔄 SubscriptionManager: Calling backend upgrade API")

        // Call backend upgrade API
        // Note: In a real app, you'd inject the UserService dependency
        // For now, we'll create a temporary instance
        let authService = AuthenticationService()
        let userService = UserService(authenticationService: authService)
        let success = await userService.upgradeUser(request)

        if success {
            print("✅ Backend upgrade successful")
            // Update local subscription status
            subscriptionStatus = .premium
            // Refresh user data to get updated subscription status
            await userService.refreshUserData()
            return true
        } else {
            print("❌ Backend upgrade failed")
            return false
        }
    }

    // MARK: - Subscription Status
    func updateSubscriptionStatus() async {
        var status: SubscriptionStatus = .free

        // Check for active subscriptions
        for await result in Transaction.currentEntitlements {
            do {
                let transaction = try checkVerified(result)

                // Check if this is a subscription product
                if productIds.contains(transaction.productID) {
                    // Check if subscription is still active
                    if let expirationDate = transaction.expirationDate {
                        if expirationDate > Date() {
                            status = .premium
                            print("✅ Active subscription found: \(transaction.productID)")
                            break
                        } else {
                            status = .expired
                            print("⏰ Expired subscription found: \(transaction.productID)")
                        }
                    } else {
                        // Non-consumable or lifetime subscription
                        status = .premium
                        print("✅ Lifetime subscription found: \(transaction.productID)")
                        break
                    }
                }
            } catch {
                print("❌ Failed to verify transaction: \(error)")
            }
        }

        subscriptionStatus = status
        print("📊 Subscription status updated: \(status)")

        // Debug: Print detailed status info
        print("📊 Current subscription status details:")
        print("📊 Status: \(status)")
        print("📊 Products loaded: \(products.count)")
        print("📊 Purchased subscriptions: \(purchasedSubscriptions.count)")
    }

    // MARK: - Backend Sync
    private func syncSubscriptionWithBackend(transaction: StoreKit.Transaction) async -> Bool {
        print("🔄 Syncing subscription with backend...")

        // For StoreKit 2, we send transaction data directly instead of receipt
        let productId = transaction.productID
        let purchaseDate = transaction.purchaseDate
        let expirationDate = transaction.expirationDate
        let environment = transaction.environment == .sandbox ? "sandbox" : "production"

        print("🔄 StoreKit 2 data:")
        print("🔄 Product ID: \(productId)")
        print("🔄 Purchase Date: \(purchaseDate)")
        print("🔄 Expiration Date: \(expirationDate?.description ?? "none")")
        print("🔄 Environment: \(environment)")

        // Create StoreKit 2 upgrade request
        let upgradeRequest = UserUpgradeRequest(
            provider: .apple,
            transactionId: String(transaction.id),
            productId: productId,
            purchaseDate: purchaseDate,
            expirationDate: expirationDate,
            environment: environment
        )

        // Call backend upgrade API using a temporary UserService instance
        let authService = AuthenticationService()
        let userService = UserService(authenticationService: authService)
        let success = await userService.upgradeUser(upgradeRequest)

        if success {
            print("✅ Backend sync successful")
            // Use the callback to refresh the main UserService instance
            if let refreshCallback = onUserDataRefresh {
                await refreshCallback()
            }
            return true
        } else {
            print("❌ Backend sync failed")
            return false
        }
    }

    // MARK: - StoreKit 2 Notes
    // Note: With StoreKit 2, we no longer need receipt-based validation.
    // All purchase validation is handled through Transaction.all and AppTransaction.shared.

    // MARK: - Transaction Listener
    private func listenForTransactions() -> Task<Void, Error> {
        return Task.detached {
            // Iterate through any transactions that don't come from a direct call to `purchase()`
            for await result in Transaction.updates {
                do {
                    let transaction = try await self.checkVerified(result)

                    print("🔄 Transaction update: \(transaction.productID)")

                    // Update subscription status
                    await self.updateSubscriptionStatus()

                    // Only sync with backend for new, active purchases
                    let fiveMinutesAgo = Date().addingTimeInterval(-300)
                    let isRecent = transaction.purchaseDate > fiveMinutesAgo
                    let isActive = transaction.expirationDate == nil || transaction.expirationDate! > Date()
                    let isNotRevoked = transaction.revocationDate == nil

                    if isRecent && isActive && isNotRevoked {
                        print("🔄 New active transaction detected - syncing with backend")
                        _ = await self.syncSubscriptionWithBackend(transaction: transaction)
                    } else {
                        print("🔄 Existing/expired transaction detected - skipping backend sync")
                        print("🔄   Recent: \(isRecent), Active: \(isActive), Not Revoked: \(isNotRevoked)")
                    }

                    // Always finish the transaction
                    await transaction.finish()

                } catch {
                    print("❌ Transaction verification failed: \(error)")
                }
            }
        }
    }

    // MARK: - Verification
    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        // Check whether the JWS passes StoreKit verification
        switch result {
        case .unverified:
            throw StoreError.failedVerification
        case .verified(let safe):
            return safe
        }
    }
}

// MARK: - Store Error
enum StoreError: Error, LocalizedError {
    case failedVerification

    var errorDescription: String? {
        switch self {
        case .failedVerification:
            return "Transaction verification failed"
        }
    }
}

    // MARK: - User Upgrade Request Model
    struct UserUpgradeRequest {
        let provider: SubscriptionProvider
        let transactionId: String
        let productId: String
        let purchaseDate: Date
        let expirationDate: Date?
        let environment: String

        // StoreKit 2 initializer
        init(provider: SubscriptionProvider, transactionId: String, productId: String, purchaseDate: Date, expirationDate: Date? = nil, environment: String) {
            self.provider = provider
            self.transactionId = transactionId
            self.productId = productId
            self.purchaseDate = purchaseDate
            self.expirationDate = expirationDate
            self.environment = environment
        }
    }

enum SubscriptionProvider: String, CaseIterable {
    case apple = "apple"
    case google = "google"
}
