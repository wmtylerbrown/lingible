import SwiftUI

// MARK: - Lingible Color System
extension Color {

    // MARK: - Primary Colors
    static let lingiblePrimary = Color("LingiblePrimary") // Will fallback to default if not in assets
    static let lingibleSecondary = Color("LingibleSecondary")

    // MARK: - Background Colors
    static let lingibleBackground = Color("LingibleBackground")
    static let lingibleLightBackground = Color("LingibleLightBackground")

    // MARK: - Text Colors
    static let lingibleDark = Color("LingibleDark")
    static let lingibleLight = Color("LingibleLight")

    // MARK: - Status Colors
    static let lingibleSuccess = Color("LingibleSuccess")
    static let lingibleError = Color("LingibleError")
    static let lingibleWarning = Color("LingibleWarning")

    // MARK: - Default Fallbacks (if assets are missing)
    static var defaultLingiblePrimary: Color {
        Color(red: 0.27, green: 0.51, blue: 0.96) // Nice blue
    }

    static var defaultLingibleSecondary: Color {
        Color(red: 0.56, green: 0.56, blue: 0.58) // Gray
    }

    static var defaultLingibleBackground: Color {
        Color(red: 0.95, green: 0.95, blue: 0.97) // Light gray
    }

    static var defaultLingibleLightBackground: Color {
        Color.white
    }
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
