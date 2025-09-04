import SwiftUI
import LingibleAPI

struct ProfileView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @StateObject private var authService = AuthenticationService()
    @State private var showingSignOutAlert = false
    @State private var showingThemePicker = false
    @State private var showingNotificationsSettings = false
    @State private var showingUpgradeSheet = false

    var body: some View {
        NavigationView {
            List {
                // User Info Section
                Section {
                    userInfoView
                }

                // Usage & Limits Section
                Section(header: Text("Usage & Limits")) {
                    if let usage = appCoordinator.userService.userUsage {
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
                    settingsRow(icon: "star", title: "Upgrade to Premium", action: { showingUpgradeSheet = true })
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

                            if appCoordinator.userService.isLoading {
                                ProgressView()
                                    .scaleEffect(0.8)
                            }
                        }
                    }

                    if let lastProfileUpdate = appCoordinator.userService.lastProfileUpdate {
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

                    if let lastUsageUpdate = appCoordinator.userService.lastUsageUpdate {
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
                    // TODO: Implement actual upgrade flow
                    print("Upgrade to Premium tapped")
                },
                onDismiss: {
                    showingUpgradeSheet = false
                },
                userUsage: appCoordinator.userService.userUsage
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
                if let profile = appCoordinator.userService.userProfile {
                    Text(profile.email ?? "Lingible User")
                        .font(.headline)
                        .fontWeight(.semibold)
                        .lineLimit(1)
                } else {
                    Text("Lingible User")
                        .font(.headline)
                        .fontWeight(.semibold)
                }

                if let profile = appCoordinator.userService.userProfile {
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
                    if let usage = appCoordinator.userService.userUsage {
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
        if let url = URL(string: "https://example.com/help") {
            UIApplication.shared.open(url)
        }
    }

    private func contactSupport() {
        if let url = URL(string: "mailto:support@example.com") {
            UIApplication.shared.open(url)
        }
    }

    private func openTerms() {
        if let url = URL(string: "https://example.com/terms") {
            UIApplication.shared.open(url)
        }
    }

    private func openPrivacy() {
        if let url = URL(string: "https://example.com/privacy") {
            UIApplication.shared.open(url)
        }
    }
}

#Preview {
    ProfileView()
        .environmentObject(AppCoordinator())
}
