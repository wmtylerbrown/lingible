import SwiftUI
import Combine
import LingibleAPI
import Amplify

struct TranslationView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @State private var inputText = ""
    @State private var showInputCard = true
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var translationHistory: [TranslationHistoryItem] = []
    @FocusState private var isInputFocused: Bool

    var body: some View {
        NavigationView {
            ZStack {
                Color.lingibleBackground
                    .ignoresSafeArea()

                VStack(spacing: 0) {
                    // Header
                    headerView

                    // Content
                    if showInputCard {
                        inputCardView
                            .padding(.horizontal, 20)
                            .padding(.top, 20)
                            .animation(.spring(response: 0.6, dampingFraction: 0.8), value: showInputCard)
                    }

                    // Results
                    if !translationHistory.isEmpty {
                        translationHistoryView
                    }

                    Spacer()
                }
            }
            .navigationBarHidden(true)
            .onTapGesture {
                // Dismiss keyboard when tapping outside
                if isInputFocused {
                    isInputFocused = false
                }
            }
            .onAppear {
                loadCachedTranslations()
                // Auto-focus the input field when the view appears
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    isInputFocused = true
                }
            }
            .alert("Translation Error", isPresented: .constant(errorMessage != nil)) {
                Button("OK") {
                    errorMessage = nil
                }
            } message: {
                if let errorMessage = errorMessage {
                    Text(errorMessage)
                }
            }
        }
    }

    // MARK: - Header View
    private var headerView: some View {
        HStack {
            // Logo + Wordmark
            HStack(spacing: 8) {
                Image("LingibleLogo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 40, height: 40)

                Image("WordmarkMedium")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(height: 30)
            }

            Spacer()

            // New translation button
            Button(action: {
                inputText = ""
                withAnimation(.spring()) {
                    showInputCard = true
                }
            }) {
                Image(systemName: "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(.lingiblePrimary)
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 8)
        .padding(.bottom, 16)
    }

    // MARK: - Input Card View
    private var inputCardView: some View {
        VStack(spacing: 20) {
            // Title
            VStack(spacing: 8) {
                Text("Translate Gen Z to English")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.lingiblePrimary)

                Text("Enter Gen Z slang or expressions to get their meaning")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }

            // Input field
            TextEditor(text: $inputText)
                .frame(minHeight: 80)
                .padding(12)
                .background(Color.white)
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(isInputFocused ? Color.lingiblePrimary : Color.lingiblePrimary.opacity(0.2), lineWidth: isInputFocused ? 2 : 1)
                )
                .focused($isInputFocused)
                .onTapGesture {
                    isInputFocused = true
                }
                .toolbar {
                    ToolbarItemGroup(placement: .keyboard) {
                        Spacer()
                        Button("Done") {
                            isInputFocused = false
                        }
                        .foregroundColor(.lingiblePrimary)
                    }
                }

            // Translate button
            Button(action: translate) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                            .scaleEffect(0.8)
                    } else {
                        Image(systemName: "arrow.right")
                            .font(.headline)
                    }

                    Text(isLoading ? "Translating..." : "Translate")
                        .font(.headline)
                        .fontWeight(.semibold)
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(
                    inputText.isEmpty || isLoading
                    ? Color.lingiblePrimary.opacity(0.5)
                    : Color.lingiblePrimary
                )
                .cornerRadius(25)
                .scaleAnimation()
            }
            .disabled(inputText.isEmpty || isLoading)
        }
        .padding(24)
        .background(Color.white)
        .cornerRadius(20)
        .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)
    }

    // MARK: - Translation History View
    private var translationHistoryView: some View {
        VStack(spacing: 16) {
            HStack {
                Text("Recent Translations")
                    .font(.headline)
                    .fontWeight(.semibold)

                Spacer()

                Button("Clear") {
                    translationHistory.removeAll()
                    saveCachedTranslations()
                }
                .foregroundColor(.red)
            }
            .padding(.horizontal, 20)

            ScrollView {
                LazyVStack(spacing: 16) {
                    ForEach(translationHistory) { translation in
                        TranslationResultCard(translation: translation)
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 20)
            }
        }
    }

    // MARK: - Actions
    private func translate() {
        guard !inputText.isEmpty else { return }

        // Dismiss keyboard
        isInputFocused = false

        Task {
            await performTranslation(text: inputText)

            // Hide input card after successful translation
            if !translationHistory.isEmpty {
                withAnimation(.spring()) {
                    showInputCard = false
                }
            }
        }
    }

    private func performTranslation(text: String) async {
        print("🔍 TranslationView: Starting translation for text: '\(text)'")
        isLoading = true
        errorMessage = nil

        do {
            // Get current user from the shared authentication service
            print("🔍 TranslationView: Attempting to get current user...")
            guard let user = try await getCurrentUser() else {
                print("❌ TranslationView: No user found")
                errorMessage = "You need to sign in to translate text"
                isLoading = false
                return
            }

            print("✅ TranslationView: Found current user: \(user.id)")

            // Get the JWT token using the centralized auth service
            print("🔍 TranslationView: Getting JWT token from centralized auth service...")

            let accessToken = try await appCoordinator.authenticationService.getAuthToken()
            print("✅ TranslationView: Got token: \(String(accessToken.prefix(20)))...")

            // Configure API client with auth token
            let authHeader = "Bearer \(accessToken)"
            LingibleAPIAPI.customHeaders["Authorization"] = authHeader

            // Log what we're sending in the Authorization header
            print("🔍 TranslationView: Setting Authorization header:")
            print("   - Header value: \(authHeader)")
            print("   - Header length: \(authHeader.count) characters")
            print("   - Bearer prefix: \(authHeader.hasPrefix("Bearer ") ? "✅ Present" : "❌ Missing")")

            // Create translation request using the generated API
            let request = TranslationRequest(
                text: text,
                direction: .genzToEnglish
            )

            // Make API call
            let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<TranslationResponse, Error>) in
                TranslationAPI.translatePost(translationRequest: request) { response, error in
                    if let error = error {
                        continuation.resume(throwing: error)
                    } else if let response = response {
                        continuation.resume(returning: response)
                    } else {
                        continuation.resume(throwing: TranslationError.invalidResponse)
                    }
                }
            }

            // Create history item
            let historyItem = TranslationHistoryItem(
                id: UUID().uuidString,
                originalText: text,
                translatedText: response.translatedText ?? "",
                createdAt: Date()
            )

            // Add to history (most recent first)
            translationHistory.insert(historyItem, at: 0)

            // Keep only last 20 translations for performance
            if translationHistory.count > 20 {
                translationHistory = Array(translationHistory.prefix(20))
            }

            // Cache the translations
            saveCachedTranslations()

        } catch {
            errorMessage = error.localizedDescription
            print("❌ Translation failed: \(error)")
        }

        isLoading = false
    }

    private func getCurrentUser() async throws -> AuthenticatedUser? {
        print("🔍 TranslationView: Getting current user...")

        // Use the direct method to get the current user value
        if let currentUser = appCoordinator.authenticationService.getCurrentUserValue() {
            print("✅ TranslationView: Found current user: \(currentUser.id)")
            return currentUser
        }

        print("⚠️ TranslationView: No current user found, checking authentication status...")

        // If no current user, try to check authentication status
        let isAuthenticated = await appCoordinator.authenticationService.checkAuthenticationStatus()
        print("🔍 TranslationView: Authentication status check result: \(isAuthenticated)")

        if isAuthenticated {
            let userAfterCheck = appCoordinator.authenticationService.getCurrentUserValue()
            print("🔍 TranslationView: User after auth check: \(userAfterCheck?.id ?? "nil")")
            return userAfterCheck
        }

        print("❌ TranslationView: No authenticated user found")
        return nil
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
}

// MARK: - Translation Result Card
struct TranslationResultCard: View {
    let translation: TranslationHistoryItem

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .font(.title2)
                    .foregroundColor(.green)

                Text("Translation")
                    .font(.headline)
                    .fontWeight(.semibold)

                Spacer()

                Text(translation.createdAt, style: .time)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            // Original text
            VStack(alignment: .leading, spacing: 8) {
                Text("Gen Z:")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.originalText)
                    .font(.body)
                    .padding(12)
                    .background(Color.lingibleSecondary.opacity(0.1))
                    .cornerRadius(8)
            }

            // Translated text
            VStack(alignment: .leading, spacing: 8) {
                Text("Translation:")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.translatedText)
                    .font(.body)
                    .padding(12)
                    .background(Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(8)
            }
        }
        .padding(20)
        .cardStyle()
    }
}

#Preview {
    TranslationView()
        .environmentObject(AppCoordinator())
}
