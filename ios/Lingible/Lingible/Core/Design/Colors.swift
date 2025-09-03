import SwiftUI

// MARK: - Lingible Color System
extension Color {

    // MARK: - Background Colors (using auto-generated asset symbols)
    static let lingibleLightBackground = Color.white

    // MARK: - Text Colors
    static let lingibleDark = Color.black
    static let lingibleLight = Color.white

    // MARK: - Status Colors
    static let lingibleSuccess = Color.green
    static let lingibleError = Color.red
    static let lingibleWarning = Color.orange
}

// MARK: - Theme Manager
@MainActor
final class ThemeManager: ObservableObject {
    static let shared = ThemeManager()

    @Published var currentTheme: AppTheme = .system

    private init() {}

    func setTheme(_ theme: AppTheme) {
        currentTheme = theme
        UserDefaults.standard.set(theme.rawValue, forKey: "selected_theme")
    }

    func getCurrentColorScheme() -> ColorScheme? {
        switch currentTheme {
        case .light:
            return .light
        case .dark:
            return .dark
        case .system:
            return nil
        }
    }

    enum AppTheme: String, CaseIterable {
        case light = "light"
        case dark = "dark"
        case system = "system"

        var displayName: String {
            switch self {
            case .light:
                return "Light"
            case .dark:
                return "Dark"
            case .system:
                return "System"
            }
        }

        var icon: String {
            switch self {
            case .light:
                return "sun.max"
            case .dark:
                return "moon"
            case .system:
                return "gear"
            }
        }
    }
}
