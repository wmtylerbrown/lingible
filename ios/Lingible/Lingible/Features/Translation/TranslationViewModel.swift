import Foundation
import Combine
import LingibleAPI

// MARK: - Translation View Model
@MainActor
final class TranslationViewModel: ObservableObject {

    // MARK: - Published Properties
    @Published var translationHistory: [TranslationHistoryItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    // MARK: - Dependencies
    private let translationService: TranslationServiceProtocol
    private let authenticationService: AuthenticationServiceProtocol

    // MARK: - Private Properties
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization
    init(
        translationService: TranslationServiceProtocol,
        authenticationService: AuthenticationServiceProtocol
    ) {
        self.translationService = translationService
        self.authenticationService = authenticationService

        // Load cached translations on init
        loadCachedTranslations()
    }



    // MARK: - Public Methods
    func translate(text: String, direction: TranslationDirection? = nil) async {
        guard !text.isEmpty else { return }

        isLoading = true
        errorMessage = nil

        do {
            let result = try await translationService.translate(text: text, direction: direction)

            let historyItem = TranslationHistoryItem(
                id: UUID().uuidString,
                originalText: text,
                translatedText: result.translatedText,
                createdAt: Date(),
                direction: direction ?? .genzToStandard
            )

            // Add to history (most recent first)
            translationHistory.insert(historyItem, at: 0)

            // Keep only last 5 translations for performance
            if translationHistory.count > 5 {
                translationHistory = Array(translationHistory.prefix(5))
            }

            // Cache the translations
            saveCachedTranslations()

        } catch {
            errorMessage = error.localizedDescription
            print("❌ Translation failed: \(error)")
        }

        isLoading = false
    }

    func clearHistory() {
        translationHistory.removeAll()
        UserDefaults.standard.removeObject(forKey: "cached_translations")
    }

    // MARK: - Private Methods
    private func loadCachedTranslations() {
        guard let data = UserDefaults.standard.data(forKey: "cached_translations") else {
            return
        }

        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            translationHistory = try decoder.decode([TranslationHistoryItem].self, from: data)
        } catch {
            print("❌ Failed to load cached translations: \(error)")
        }
    }

    private func saveCachedTranslations() {
        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            let data = try encoder.encode(translationHistory)
            UserDefaults.standard.set(data, forKey: "cached_translations")
        } catch {
            print("❌ Failed to save cached translations: \(error)")
        }
    }
}

// MARK: - Translation History Item
struct TranslationHistoryItem: Codable, Identifiable {
    let id: String
    let originalText: String
    let translatedText: String
    let createdAt: Date
    let direction: TranslationDirection
}
