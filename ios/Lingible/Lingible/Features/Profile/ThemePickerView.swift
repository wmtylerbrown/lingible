import SwiftUI

struct ThemePickerView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("selectedTheme") private var selectedTheme = "system"

    private let themes = [
        ("system", "Automatic", "iphone", "Follows system appearance"),
        ("light", "Light", "sun.max", "Always light mode"),
        ("dark", "Dark", "moon", "Always dark mode")
    ]

    var body: some View {
        NavigationView {
            List {
                ForEach(themes, id: \.0) { theme in
                    Button(action: {
                        selectedTheme = theme.0
                    }) {
                        HStack {
                            Image(systemName: theme.2)
                                .font(.title2)
                                .foregroundColor(.lingiblePrimary)
                                .frame(width: 30)

                            VStack(alignment: .leading, spacing: 2) {
                                Text(theme.1)
                                    .font(.headline)
                                    .foregroundColor(.primary)

                                Text(theme.3)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            if selectedTheme == theme.0 {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(.lingiblePrimary)
                                    .font(.title2)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
            .navigationTitle("Theme")
            .navigationBarTitleDisplayMode(.inline)
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
    ThemePickerView()
}
