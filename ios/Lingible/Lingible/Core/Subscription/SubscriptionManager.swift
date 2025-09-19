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
    private let productIds: [String] = ["com.lingible.lingible.premium.monthly"]
    private var updateListenerTask: Task<Void, Error>? = nil

    // Always use real StoreKit products (no development mode)

    // MARK: - Subscription Status
    enum SubscriptionStatus {
        case unknown
        case free
        case premium
        case expired
    }

    // MARK: - Initialization
    init() {
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

            // Check if we're in sandbox mode
            if let receiptURL = Bundle.main.appStoreReceiptURL {
                print("🛒 Receipt URL: \(receiptURL)")
                print("🛒 Sandbox Mode: \(receiptURL.lastPathComponent == "sandboxReceipt")")
            }

            let storeProducts = try await Product.products(for: productIds)

            // Sort products by price (cheapest first)
            self.products = storeProducts.sorted { $0.price < $1.price }

            print("🛒 Loaded \(products.count) subscription products")
            for product in products {
                print("  - \(product.displayName): \(product.displayPrice)")
            }

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

                // Sync with backend
                await syncSubscriptionWithBackend(transaction: transaction)

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
    }

    // MARK: - Backend Sync
    private func syncSubscriptionWithBackend(transaction: StoreKit.Transaction) async {
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

        // Call backend upgrade API
        // Note: In a real app, you'd inject the UserService dependency
        // For now, we'll create a temporary instance
        let authService = AuthenticationService()
        let userService = UserService(authenticationService: authService)
        let success = await userService.upgradeUser(upgradeRequest)

        if success {
            print("✅ Backend sync successful")
        } else {
            print("❌ Backend sync failed")
        }
    }

    private func getReceiptData() async -> String {
        // For StoreKit 2, we need to get the app receipt from the bundle
        do {
            // Get the receipt data from the app's bundle
            guard let receiptURL = Bundle.main.appStoreReceiptURL else {
                print("❌ No receipt URL found")
                return "no_receipt_url"
            }

            print("🛒 Attempting to read receipt from: \(receiptURL)")

            // Check if the receipt file exists
            guard FileManager.default.fileExists(atPath: receiptURL.path) else {
                print("❌ Receipt file does not exist at: \(receiptURL.path)")
                // For sandbox testing, create a mock receipt
                return createMockReceiptData()
            }

            let receiptData = try Data(contentsOf: receiptURL)
            print("✅ Successfully read receipt data (\(receiptData.count) bytes)")
            return receiptData.base64EncodedString()
        } catch {
            print("❌ Error getting receipt data: \(error)")
            // Fallback: create a receipt-like structure for testing
            return createMockReceiptData()
        }
    }

    private func createMockReceiptData() -> String {
        print("🛒 Creating mock receipt data for sandbox testing")
        let receiptInfo = [
            "bundle_id": Bundle.main.bundleIdentifier ?? "",
            "application_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "",
            "receipt_type": "ProductionSandbox",
            "in_app": []
        ] as [String: Any]

        if let jsonData = try? JSONSerialization.data(withJSONObject: receiptInfo),
           let jsonString = String(data: jsonData, encoding: .utf8) {
            return jsonString.data(using: .utf8)?.base64EncodedString() ?? "fallback_receipt_data"
        }

        return "fallback_receipt_data"
    }

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

                    // Sync with backend if needed
                    if transaction.revocationDate == nil {
                        await self.syncSubscriptionWithBackend(transaction: transaction)
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
