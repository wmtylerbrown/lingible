import SwiftUI

struct NotificationsSettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("notificationsEnabled") private var notificationsEnabled = true
    @AppStorage("dailyReminderEnabled") private var dailyReminderEnabled = false
    @AppStorage("upgradeNotificationsEnabled") private var upgradeNotificationsEnabled = true
    @State private var reminderTime = Date()

    var body: some View {
        NavigationView {
            List {
                Section {
                    Toggle(isOn: $notificationsEnabled) {
                        HStack {
                            Image(systemName: "bell")
                                .foregroundColor(.lingiblePrimary)
                                .frame(width: 24)
                            Text("Enable Notifications")
                                .font(.headline)
                        }
                    }
                } footer: {
                    Text("Receive notifications about your translations and account")
                }

                if notificationsEnabled {
                    Section(header: Text("Daily Reminders"), footer: Text("Get reminded to use your daily translation allowance")) {
                        Toggle(isOn: $dailyReminderEnabled) {
                            HStack {
                                Image(systemName: "clock")
                                    .foregroundColor(.lingiblePrimary)
                                    .frame(width: 24)
                                Text("Daily Translation Reminder")
                            }
                        }

                        if dailyReminderEnabled {
                            HStack {
                                Image(systemName: "clock.fill")
                                    .foregroundColor(.lingiblePrimary)
                                    .frame(width: 24)
                                Text("Reminder Time")
                                Spacer()
                                DatePicker("", selection: $reminderTime, displayedComponents: .hourAndMinute)
                                    .labelsHidden()
                            }
                        }
                    }

                    Section(header: Text("Account Notifications"), footer: Text("Receive notifications about premium features and upgrades")) {
                        Toggle(isOn: $upgradeNotificationsEnabled) {
                            HStack {
                                Image(systemName: "star")
                                    .foregroundColor(.lingiblePrimary)
                                    .frame(width: 24)
                                Text("Premium Upgrade Offers")
                            }
                        }
                    }
                }

                Section(header: Text("Notification Types")) {
                    HStack {
                        Image(systemName: "checkmark.circle")
                            .foregroundColor(.green)
                            .frame(width: 24)
                        Text("Translation Complete")
                        Spacer()
                        Text("Always")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    HStack {
                        Image(systemName: "exclamationmark.triangle")
                            .foregroundColor(.orange)
                            .frame(width: 24)
                        Text("Daily Limit Reached")
                        Spacer()
                        Text("Always")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    HStack {
                        Image(systemName: "star.fill")
                            .foregroundColor(.yellow)
                            .frame(width: 24)
                        Text("Premium Features")
                        Spacer()
                        Text(upgradeNotificationsEnabled ? "Enabled" : "Disabled")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Notifications")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                // Load saved reminder time or use default
                if let savedTime = UserDefaults.standard.object(forKey: "reminderTime") as? Date {
                    reminderTime = savedTime
                } else {
                    reminderTime = Calendar.current.date(from: DateComponents(hour: 9, minute: 0)) ?? Date()
                }
            }
            .onDisappear {
                // Save reminder time when view disappears
                UserDefaults.standard.set(reminderTime, forKey: "reminderTime")
            }
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

#Preview {
    NotificationsSettingsView()
}
