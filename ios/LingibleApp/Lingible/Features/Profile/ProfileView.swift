import SwiftUI

struct ProfileView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @StateObject private var authService = AuthenticationService()
    @State private var showingSignOutAlert = false

    var body: some View {
        NavigationView {
            List {
                // User Info Section
                Section {
                    userInfoView
                }

                // Settings Section
                Section("Settings") {
                    settingsRow(icon: "bell", title: "Notifications", action: {})
                    settingsRow(icon: "paintbrush", title: "Theme", action: {})
                    settingsRow(icon: "star", title: "Upgrade to Premium", action: {})
                }

                // Support Section
                Section("Support") {
                    settingsRow(icon: "questionmark.circle", title: "Help & FAQ", action: {})
                    settingsRow(icon: "envelope", title: "Contact Support", action: {})
                    settingsRow(icon: "doc.text", title: "Terms of Service", action: {})
                    settingsRow(icon: "hand.raised", title: "Privacy Policy", action: {})
                }

                // Account Section
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
                Text("Lingible User")
                    .font(.headline)
                    .fontWeight(.semibold)

                Text("user@example.com")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                // User tier badge
                HStack {
                    Text("Free User")
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(.lingibleSecondary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(Color.lingibleSecondary.opacity(0.1))
                        .cornerRadius(8)

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
}

#Preview {
    ProfileView()
        .environmentObject(AppCoordinator())
}
