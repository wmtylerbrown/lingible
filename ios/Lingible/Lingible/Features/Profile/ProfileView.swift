import SwiftUI
import StoreKit
import LingibleAPI
import AppTrackingTransparency

struct ProfileView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @State private var showingSignOutAlert = false
    @State private var showingDeleteAccountAlert = false
    @State private var showingDeleteConfirmation = false
    @State private var deleteConfirmationText = ""
    @State private var isDeletingAccount = false
    @State private var showingThemePicker = false
    @State private var showingUpgradeSheet = false
    @State private var showingClearCacheAlert = false
    @State private var showingSubscriptionWarning = false
    @State private var showingTrackingSettingsAlert = false

    var body: some View {
        NavigationView {
            List {
                // User Info Section
                Section {
                    userInfoView
                }

                // Usage & Limits Section
                Section(header: Text("Usage & Limits")) {
                    if let usage = appCoordinator.userUsage {
                        usageRow(title: "Daily Translations", value: "\(usage.dailyUsed)/\(usage.dailyLimit)")
                        usageRow(title: "Text Length Limit", value: "\(usage.currentMaxTextLength) characters")
                        usageRow(title: "Account Tier", value: tierDisplayName(usage.tier))

                        usageRow(title: "Next Reset", value: usage.resetDate)
                    } else {
                        HStack {
                            ProgressView()
                                .scaleEffect(0.8)
                            Text("Loading usage data...")
                                .foregroundColor(.secondary)
                        }
                    }
                }

                // Settings Section
                Section(header: Text("Preferences")) {
                    settingsRow(icon: "paintbrush", title: "Theme", action: { showingThemePicker = true })
                    settingsRow(icon: "trash", title: "Clear Cache", action: { showingClearCacheAlert = true })

                    // Show different options based on user tier
                    if let usage = appCoordinator.userUsage, usage.tier == .premium {
                        // Premium user - show subscription management
                        settingsRow(icon: "creditcard", title: "Manage Subscriptions", action: { manageSubscriptions() })
                        settingsRow(icon: "arrow.clockwise.circle", title: "Restore Purchases", action: { restorePurchases() })
                    } else {
                        // Free user - show upgrade option
                        settingsRow(icon: "star", title: "Upgrade to Premium", action: { showingUpgradeSheet = true })
                        settingsRow(icon: "arrow.clockwise.circle", title: "Restore Purchases", action: { restorePurchases() })
                    }
                }

                // Privacy Settings Section
                Section(header: Text("Privacy & Tracking")) {
                    privacySettingsRow()
                }

                // Account Section
                Section(header: Text("Account")) {
                    Button(action: {
                        Task {
                            await appCoordinator.userService.refreshUserData()
                        }
                    }) {
                        HStack {
                            Image(systemName: "arrow.clockwise")
                                .foregroundColor(.lingiblePrimary)
                                .frame(width: 24)

                            Text("Refresh User Data")
                                .foregroundColor(.primary)

                            Spacer()

                            if appCoordinator.userServiceIsLoading {
                                ProgressView()
                                    .scaleEffect(0.8)
                            }
                        }
                    }

                    if let lastProfileUpdate = appCoordinator.lastProfileUpdate {
                        HStack {
                            Image(systemName: "clock")
                                .foregroundColor(.secondary)
                                .frame(width: 24)

                            Text("Profile updated: \(lastProfileUpdate, style: .time)")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Spacer()
                        }
                    }

                    if let lastUsageUpdate = appCoordinator.lastUsageUpdate {
                        HStack {
                            Image(systemName: "clock")
                                .foregroundColor(.secondary)
                                .frame(width: 24)

                            Text("Usage updated: \(lastUsageUpdate, style: .time)")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Spacer()
                        }
                    }
                }

                // Support Section
                Section(header: Text("Support")) {
                    settingsRow(icon: "envelope", title: "Contact Support", action: { contactSupport() })
                    settingsRow(icon: "doc.text", title: "Terms of Service", action: { openTerms() })
                    settingsRow(icon: "hand.raised", title: "Privacy Policy", action: { openPrivacy() })
                }

                // Sign Out Section
                Section {
                    Button(action: { showingSignOutAlert = true }) {
                        HStack {
                            Image(systemName: "rectangle.portrait.and.arrow.right")
                                .foregroundColor(.red)
                            Text("Sign Out")
                                .foregroundColor(.red)
                            Spacer()
                        }
                    }
                }

                // Account Deletion Section
                Section(header: Text("Danger Zone"), footer: Text("This action cannot be undone. All your data will be permanently deleted.")) {
                    Button(action: { showingDeleteAccountAlert = true }) {
                        HStack {
                            Image(systemName: "trash")
                                .foregroundColor(.red)
                            Text("Delete Account")
                                .foregroundColor(.red)
                            Spacer()
                        }
                    }
                    .disabled(isDeletingAccount)
                }
            }
            .navigationTitle("Profile")
        }
        .sheet(isPresented: $showingThemePicker) {
            ThemePickerView()
        }
        .sheet(isPresented: $showingUpgradeSheet) {
            UpgradePromptView(
                translationCount: appCoordinator.userUsage?.dailyUsed ?? 0,
                onUpgrade: {
                    // Refresh user data after successful upgrade
                    Task {
                        await appCoordinator.userService.refreshUserData()
                    }
                },
                onDismiss: {
                    showingUpgradeSheet = false
                },
                userUsage: appCoordinator.userUsage
            )
        }
        .alert("Sign Out", isPresented: $showingSignOutAlert) {
            Button("Cancel", role: .cancel) { }
            Button("Sign Out", role: .destructive) {
                appCoordinator.signOut()
            }
        } message: {
            Text("Are you sure you want to sign out?")
        }
        .alert("Clear Cache", isPresented: $showingClearCacheAlert) {
            Button("Cancel", role: .cancel) { }
            Button("Clear All Cache", role: .destructive) {
                clearAllCache()
            }
        } message: {
            Text("This will clear all cached data including translation history and trending data. This action cannot be undone.")
        }
        .alert("Delete Account", isPresented: $showingDeleteAccountAlert) {
            Button("Cancel", role: .cancel) { }
            Button("Continue", role: .destructive) {
                // Check if user has active subscription
                if let usage = appCoordinator.userUsage, usage.tier == .premium {
                    showingSubscriptionWarning = true
                } else {
                    showingDeleteConfirmation = true
                }
            }
        } message: {
            Text("Are you sure you want to delete your account? This will permanently delete all your data including translations, preferences, and subscription information. This action cannot be undone.")
        }
        .alert("Confirm Account Deletion", isPresented: $showingDeleteConfirmation) {
            TextField("Type DELETE to confirm", text: $deleteConfirmationText)
            Button("Cancel", role: .cancel) {
                deleteConfirmationText = ""
            }
            Button("Delete Account", role: .destructive) {
                Task {
                    await deleteAccount()
                }
            }
            .disabled(deleteConfirmationText != "DELETE" || isDeletingAccount)
        } message: {
            Text("Type 'DELETE' in the text field above to confirm account deletion.")
        }
        .alert("Cancel Subscription First", isPresented: $showingSubscriptionWarning) {
            Button("Manage Subscriptions") {
                manageSubscriptions()
            }
            Button("Continue Anyway", role: .destructive) {
                showingDeleteConfirmation = true
            }
            Button("Cancel", role: .cancel) { }
        } message: {
            Text("You have an active subscription. Please cancel it first to avoid future charges, or continue with account deletion anyway.")
        }
        .alert("Tracking Settings", isPresented: $showingTrackingSettingsAlert) {
            Button("Open Settings") {
                openTrackingSettings()
            }
            Button("Cancel", role: .cancel) { }
        } message: {
            Text("To change your tracking permission, you'll need to go to your device's Privacy & Security settings. This will open the Settings app where you can manage App Tracking permissions.")
        }
        .onAppear {
            print("🔥 ProfileView onAppear called!")
            Task {
                print("🔥 About to call loadUserData")
                await appCoordinator.userService.loadUserData(forceRefresh: false)
                print("🔥 loadUserData completed")
            }
        }
    }

    // MARK: - User Info View
    private var userInfoView: some View {
        HStack(spacing: 16) {
            // Profile image placeholder
            ZStack {
                Circle()
                    .fill(Color.lingiblePrimary.opacity(0.1))
                    .frame(width: 60, height: 60)

                Image(systemName: "person.fill")
                    .font(.title2)
                    .foregroundColor(.lingiblePrimary)
            }

            // User details
            VStack(alignment: .leading, spacing: 4) {
                if let profile = appCoordinator.userProfile {
                    Text(profile.email ?? "Lingible User")
                        .font(.headline)
                        .fontWeight(.semibold)
                        .lineLimit(1)
                } else {
                    Text("Lingible User")
                        .font(.headline)
                        .fontWeight(.semibold)
                }

                if let profile = appCoordinator.userProfile {
                    Text(profile.email ?? "No email")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                } else {
                    Text("Loading...")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                // User tier badge
                HStack {
                    if let usage = appCoordinator.userUsage {
                        Text(tierDisplayName(usage.tier))
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(usage.tier == .premium ? .yellow : .lingibleSecondary)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background((usage.tier == .premium ? Color.yellow : Color.lingibleSecondary).opacity(0.1))
                            .cornerRadius(8)
                    } else {
                        Text("Loading...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(Color.gray.opacity(0.1))
                            .cornerRadius(8)
                    }

                    Spacer()
                }
            }

            Spacer()
        }
        .padding(.vertical, 8)
    }

    // MARK: - Settings Row
    private func settingsRow(icon: String, title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(.lingiblePrimary)
                    .frame(width: 24)

                Text(title)
                    .foregroundColor(.primary)

                Spacer()

                Image(systemName: "chevron.right")
                    .foregroundColor(.secondary)
                    .font(.caption)
            }
        }
    }

    // MARK: - Usage Row
    private func usageRow(title: String, value: String) -> some View {
        HStack {
            Text(title)
                .font(.subheadline)
                .foregroundColor(.primary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
    }

    private func usageRow(title: String, value: Date) -> some View {
        HStack {
            Text(title)
                .font(.subheadline)
                .foregroundColor(.primary)
            Spacer()
            Text(value, style: .time)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Tier Display Name
    private func tierDisplayName(_ tier: UsageResponse.Tier?) -> String {
        guard let tier = tier else {
            return "Unknown Tier"
        }
        switch tier {
        case .free:
            return "Free User"
        case .premium:
            return "Premium User"
        }
    }

    // MARK: - Open Links
    private func contactSupport() {
        let email = AppConfiguration.supportEmail
        print("📧 ProfileView: Attempting to open email to: \(email)")

        if let url = URL(string: "mailto:\(email)") {
            print("📧 ProfileView: Created mailto URL: \(url)")
            if UIApplication.shared.canOpenURL(url) {
                print("📧 ProfileView: Can open URL, opening...")
                UIApplication.shared.open(url)
            } else {
                print("❌ ProfileView: Cannot open mailto URL - no email app configured")
                // Fallback: Copy email to clipboard
                UIPasteboard.general.string = email
                // You could show an alert here saying "Email copied to clipboard"
            }
        } else {
            print("❌ ProfileView: Failed to create mailto URL for: \(email)")
        }
    }

    private func openTerms() {
        if let url = URL(string: AppConfiguration.termsOfServiceURL) {
            UIApplication.shared.open(url)
        }
    }

    private func openPrivacy() {
        if let url = URL(string: AppConfiguration.privacyPolicyURL) {
            UIApplication.shared.open(url)
        }
    }

    private func restorePurchases() {
        Task {
            let subscriptionManager = SubscriptionManager()
            let success = await subscriptionManager.restorePurchases()

            if success {
                // Refresh user data to get updated subscription status
                await appCoordinator.userService.refreshUserData()
            }
        }
    }

    private func manageSubscriptions() {
        Task {
            do {
                // Use AppStore.showManageSubscriptions for iOS 15+
                if #available(iOS 15.0, *) {
                    if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene {
                        try await AppStore.showManageSubscriptions(in: windowScene)
                    }
                } else {
                    // Fallback for older iOS versions - open App Store
                    if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
                        await UIApplication.shared.open(url)
                    }
                }
            } catch {
                print("❌ Failed to open subscription management: \(error)")
                // Fallback to App Store URL
                if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
                    await UIApplication.shared.open(url)
                }
            }
        }
    }

    private func clearAllCache() {
        // Clear translation history cache
        UserDefaults.standard.removeObject(forKey: "cached_translations")

        // Clear trending data cache
        UserDefaults.standard.removeObject(forKey: "trending_cache_data")
        UserDefaults.standard.removeObject(forKey: "trending_cache_timestamp")

        // Clear any other cached data
        // UserDefaults.standard.removeObject(forKey: "user_profile_cache")
        // UserDefaults.standard.removeObject(forKey: "user_usage_cache")

        print("🗑️ All cache cleared successfully")
    }

    // MARK: - Account Deletion
    private func deleteAccount() async {
        guard deleteConfirmationText == "DELETE" else {
            print("❌ Account deletion cancelled: confirmation text mismatch")
            return
        }

        isDeletingAccount = true

        do {
            print("🗑️ Starting account deletion process...")

            // Create the account deletion request
            let request = AccountDeletionRequest(
                confirmationText: deleteConfirmationText,
                reason: "User requested account deletion via iOS app"
            )

            // Get access token and configure API client
            let accessToken = try await appCoordinator.authenticationService.getAuthToken()
            LingibleAPIAPI.customHeaders["Authorization"] = "Bearer \(accessToken)"

            // Call the API to delete the account
            let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<AccountDeletionResponse, Error>) in
                UserAPI.userAccountDelete(accountDeletionRequest: request) { data, error in
                    if let error = error {
                        continuation.resume(throwing: error)
                    } else if let data = data {
                        continuation.resume(returning: data)
                    } else {
                        continuation.resume(throwing: NSError(domain: "AccountDeletionError", code: -1, userInfo: [NSLocalizedDescriptionKey: "Unknown error occurred"]))
                    }
                }
            }

            if response.success == true {
                print("✅ Account deleted successfully")

                // Clear local data
                clearAllCache()

                // Sign out the user (this will clear authentication state)
                await MainActor.run {
                    appCoordinator.signOut()
                }
            } else {
                print("❌ Account deletion failed: \(response.message ?? "Unknown error")")
                // Show error to user
                await MainActor.run {
                    // You could show an error alert here
                    print("❌ Failed to delete account: \(response.message ?? "Unknown error")")
                }
            }

        } catch {
            print("❌ Account deletion error: \(error)")
            await MainActor.run {
                // Handle specific error cases
                if let apiError = error as? ErrorResponse {
                    handleAccountDeletionError(apiError)
                } else {
                    // Generic error handling
                    print("❌ Account deletion failed: \(error.localizedDescription)")
                }
            }
        }

        await MainActor.run {
            isDeletingAccount = false
            deleteConfirmationText = ""
        }
    }

    // MARK: - Error Handling
    private func handleAccountDeletionError(_ error: ErrorResponse) {
        switch error {
        case .error(let statusCode, let data, _, _):
            print("❌ Account deletion failed with status code: \(statusCode)")

            // Try to parse the response data as ModelErrorResponse for structured error handling
            if let data = data {
                do {
                    let errorResponse = try JSONDecoder().decode(ModelErrorResponse.self, from: data)
                    switch errorResponse.errorCode {
                    case "ACTIVE_SUBSCRIPTION_EXISTS":
                        // Show subscription warning alert
                        showingSubscriptionWarning = true
                    case "INVALID_CONFIRMATION":
                        // Show confirmation error
                        print("❌ Invalid confirmation text. Please type 'DELETE' exactly.")
                    default:
                        // Generic error handling
                        print("❌ Account deletion failed: \(errorResponse.message ?? "Unknown error")")
                    }
                } catch {
                    // If we can't parse as ModelErrorResponse, show generic error
                    print("❌ Account deletion failed: Could not parse error response")
                }
            } else {
                print("❌ Account deletion failed: No error data available")
            }
        }
    }

    // MARK: - Privacy Settings
    private func privacySettingsRow() -> some View {
        Button(action: { showingTrackingSettingsAlert = true }) {
            HStack {
                Image(systemName: trackingIcon)
                    .foregroundColor(.lingiblePrimary)
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 2) {
                    Text("App Tracking")
                        .foregroundColor(.primary)

                    Text(trackingStatusText)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .foregroundColor(.secondary)
                    .font(.caption)
            }
        }
    }

    private var trackingIcon: String {
        if #available(iOS 14, *) {
            switch ATTrackingManager.trackingAuthorizationStatus {
            case .authorized:
                return "checkmark.circle.fill"
            case .denied, .restricted:
                return "xmark.circle.fill"
            case .notDetermined:
                return "questionmark.circle.fill"
            @unknown default:
                return "questionmark.circle.fill"
            }
        } else {
            return "questionmark.circle.fill"
        }
    }

    private var trackingStatusText: String {
        if #available(iOS 14, *) {
            switch ATTrackingManager.trackingAuthorizationStatus {
            case .authorized:
                return "Enabled - Personalized ads"
            case .denied:
                return "Disabled - Non-personalized ads"
            case .restricted:
                return "Restricted - Non-personalized ads"
            case .notDetermined:
                return "Not set - Tap to configure"
            @unknown default:
                return "Unknown status"
            }
        } else {
            return "Not available on this iOS version"
        }
    }

    private func openTrackingSettings() {
        if let settingsUrl = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(settingsUrl)
        }
    }
}

#Preview {
    ProfileView()
        .environmentObject(AppCoordinator())
}
