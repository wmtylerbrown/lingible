import SwiftUI
import LingibleAPI

struct ProfileView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @State private var showingSignOutAlert = false
    @State private var showingThemePicker = false
    @State private var showingNotificationsSettings = false
    @State private var showingUpgradeSheet = false
    @State private var showingClearCacheAlert = false

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
                        usageRow(title: "Daily Translations", value: "\(usage.dailyUsed ?? 0)/\(usage.dailyLimit ?? 0)")
                        usageRow(title: "Text Length Limit", value: "\(usage.currentMaxTextLength ?? 50) characters")
                        usageRow(title: "Account Tier", value: tierDisplayName(usage.tier))

                        if let resetDate = usage.resetDate {
                            usageRow(title: "Next Reset", value: resetDate)
                        }
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
                    settingsRow(icon: "bell", title: "Notifications", action: { showingNotificationsSettings = true })
                    settingsRow(icon: "paintbrush", title: "Theme", action: { showingThemePicker = true })
                    settingsRow(icon: "trash", title: "Clear Cache", action: { showingClearCacheAlert = true })
                    settingsRow(icon: "star", title: "Upgrade to Premium", action: { showingUpgradeSheet = true })
                    settingsRow(icon: "arrow.clockwise.circle", title: "Restore Purchases", action: { restorePurchases() })
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
                    settingsRow(icon: "questionmark.circle", title: "Help & FAQ", action: { openHelpFAQ() })
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
            }
            .navigationTitle("Profile")
        }
        .sheet(isPresented: $showingThemePicker) {
            ThemePickerView()
        }
        .sheet(isPresented: $showingNotificationsSettings) {
            NotificationsSettingsView()
        }
        .sheet(isPresented: $showingUpgradeSheet) {
            UpgradePromptView(
                translationCount: nil,
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
    private func openHelpFAQ() {
        if let url = URL(string: AppConfiguration.helpFAQURL) {
            UIApplication.shared.open(url)
        }
    }

    private func contactSupport() {
        if let url = URL(string: "mailto:\(AppConfiguration.supportEmail)") {
            UIApplication.shared.open(url)
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
}

#Preview {
    ProfileView()
        .environmentObject(AppCoordinator())
}
