import SwiftUI
import LingibleAPI
import Amplify

// MARK: - User Tier Enum
// Using API-generated UsageResponse.Tier instead of hardcoded enum

struct TranslationView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @State private var inputText = ""
    @State private var showInputCard = true
    @State private var currentTranslationResult: TranslationHistoryItem?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var translationHistory: [TranslationHistoryItem] = []
    @State private var isGenZToEnglish = true // Translation direction toggle
    @State private var showingUpgradePrompt = false
    @FocusState private var isInputFocused: Bool

    // MARK: - Computed Properties
    private var userTier: UsageResponse.Tier {
        appCoordinator.userUsage?.tier ?? .free
    }

    private var maxTextLength: Int {
        appCoordinator.userUsage?.currentMaxTextLength ?? 50 // Use dynamic limit with fallback
    }

    private var isTextValid: Bool {
        !inputText.isEmpty && inputText.count <= maxTextLength
    }

    private var remainingCharacters: Int {
        maxTextLength - inputText.count
    }

    private var characterCountColor: Color {
        if remainingCharacters <= 0 {
            return .red
        } else if remainingCharacters <= 10 {
            return .orange
        } else {
            return .secondary
        }
    }

    private var tierDisplayName: String {
        switch userTier {
        case .free:
            return "Free"
        case .premium:
            return "Premium"
        }
    }

    var body: some View {
        NavigationView {
            ZStack {
                Color.lingibleBackground
                    .ignoresSafeArea()

                VStack(spacing: 0) {
                    // Header
                    CommonHeader.logoOnly()

                    // Content
                    if showInputCard {
                        inputCardView
                            .padding(.horizontal, 20)
                            .padding(.top, 20)
                            .animation(.spring(response: 0.6, dampingFraction: 0.8), value: showInputCard)
                    } else if let currentResult = currentTranslationResult {
                        currentResultCardView(translation: currentResult)
                            .padding(.horizontal, 20)
                            .padding(.top, 20)
                            .animation(.spring(response: 0.6, dampingFraction: 0.8), value: showInputCard)
                    }

                    // Results
                    if !translationHistory.isEmpty {
                        translationHistoryView
                            .padding(.top, 30)
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
                // User data is already loaded by AppCoordinator after authentication
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
            .sheet(isPresented: $showingUpgradePrompt) {
                UpgradePromptView(
                    translationCount: translationHistory.count,
                    onUpgrade: {
                        showingUpgradePrompt = false
                        // TODO: Navigate to upgrade flow
                    },
                    onDismiss: {
                        showingUpgradePrompt = false
                    },
                    userUsage: appCoordinator.userUsage
                )
            }
        }
    }

    // MARK: - Input Card View
    private var inputCardView: some View {
        VStack(spacing: 20) {
            // Translation Direction Control
            Picker("Direction", selection: $isGenZToEnglish) {
                Text("GenZ → English").tag(true)
                Text("English → GenZ").tag(false)
            }
            .pickerStyle(SegmentedPickerStyle())
            .padding(.horizontal, 16)
            .padding(.vertical, 8)

            // Title
            Text(isGenZToEnglish ? "Translate Gen Z to English" : "Translate English to Gen Z")
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(.lingiblePrimary)
                .multilineTextAlignment(.center)

            // Input field
            TextEditor(text: $inputText)
                .frame(height: 120)
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
                .overlay(
                    Group {
                        if inputText.isEmpty {
                            Text(isGenZToEnglish ? "Enter Gen Z slang to translate..." : "Enter English to translate...")
                                .foregroundColor(.secondary.opacity(0.6))
                                .padding(.leading, 16)
                                .padding(.top, 20)
                                .allowsHitTesting(false)
                        }
                    }
                )
                .onSubmit {
                    isInputFocused = false
                }

                // Character counter and tier info
                HStack {
                    // Character counter
                    HStack(spacing: 4) {
                        Text("\(inputText.count)")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(characterCountColor)

                        Text("/ \(maxTextLength)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    // Tier indicator
                    HStack(spacing: 4) {
                        Image(systemName: userTier == .premium ? "star.fill" : "person.fill")
                            .font(.caption)
                            .foregroundColor(userTier == .premium ? .yellow : .secondary)

                        Text(tierDisplayName)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.horizontal, 4)
                .padding(.top, 4)

                // Warning message for exceeded limits
                if let maxLength = appCoordinator.userUsage?.currentMaxTextLength, inputText.count > maxLength {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.orange)
                            .font(.caption)

                        Text("Text exceeds \(tierDisplayName) tier limit (\(maxTextLength) characters)")
                            .font(.caption)
                            .foregroundColor(.orange)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.orange.opacity(0.1))
                    .cornerRadius(8)
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
                    !isTextValid || isLoading
                    ? Color.lingiblePrimary.opacity(0.5)
                    : Color.lingiblePrimary
                )
                .cornerRadius(25)
                .scaleAnimation()
            }
            .disabled(!isTextValid || isLoading)
        }
        .padding(24)
        .background(Color.white)
        .cornerRadius(20)
        .shadow(color: .black.opacity(0.1), radius: 10, x: 0, y: 5)
    }

    // MARK: - Current Result Card View
    private func currentResultCardView(translation: TranslationHistoryItem) -> some View {
        VStack(spacing: 20) {
            // Header with success indicator
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .font(.title2)
                    .foregroundColor(.green)

                Text("Translation Complete")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.lingiblePrimary)

                Spacer()

                Text(translation.createdAt, style: .time)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            // Original text
            VStack(alignment: .leading, spacing: 8) {
                Text(translation.direction == .genzToStandard ? "Gen Z:" : "English:")
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
                Text(translation.direction == .genzToStandard ? "English:" : "Gen Z:")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.translatedText)
                    .font(.body)
                    .padding(12)
                    .background(Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(8)
            }

            // New translation button
            Button(action: handleNewButtonTap) {
                HStack {
                    Image(systemName: "plus.circle.fill")
                        .font(.headline)

                    Text("New Translation")
                        .font(.headline)
                        .fontWeight(.semibold)
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color.lingiblePrimary)
                .cornerRadius(25)
                .scaleAnimation()
            }
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
    private func handleNewButtonTap() {
        // If we have a current result, move it to history
        if let currentResult = currentTranslationResult {
            translationHistory.insert(currentResult, at: 0)

            // Keep only last 20 translations for performance
            if translationHistory.count > 20 {
                translationHistory = Array(translationHistory.prefix(20))
            }

            // Cache the translations
            saveCachedTranslations()
        }

        // Clear current result and show input card
        currentTranslationResult = nil
        inputText = ""
        withAnimation(.spring()) {
            showInputCard = true
        }
    }

    private func translate() {
        guard !inputText.isEmpty else { return }

        // Check if text exceeds free tier limit
        if userTier == .free && inputText.count > maxTextLength {
            showUpgradePrompt()
            return
        }

        // Dismiss keyboard
        isInputFocused = false

        Task {
            await performTranslation(text: inputText)
        }
    }

    private func showUpgradePrompt() {
        if let premiumLimit = appCoordinator.userUsage?.premiumTierMaxLength {
            errorMessage = "Text exceeds free tier limit. Upgrade to Premium to translate longer texts (up to \(premiumLimit) characters)."
        } else {
            errorMessage = "Text exceeds free tier limit. Upgrade to Premium to translate longer texts."
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
                direction: isGenZToEnglish ? .genzToEnglish : .englishToGenz
            )

            // Make API call
            let response = try await TranslationAPI.translatePost(translationRequest: request)

            // Create history item
            let historyItem = TranslationHistoryItem(
                id: UUID().uuidString,
                originalText: text,
                translatedText: response.translatedText ?? "",
                createdAt: Date(),
                direction: isGenZToEnglish ? .genzToStandard : .standardToGenz
            )

            // Set as current result and hide input card
            currentTranslationResult = historyItem
            withAnimation(.spring()) {
                showInputCard = false
            }

            // Check if we should show upgrade prompt for free users
            if userTier == .free && translationHistory.count > 0 && translationHistory.count % 3 == 0 {
                // Show upgrade prompt every 3 translations
                DispatchQueue.main.async {
                    showingUpgradePrompt = true
                }
            }

        } catch {
            // TEMPORARY: Log full error details to understand the 429 response structure
            print("❌ Translation failed: \(error)")
            print("❌ Error type: \(type(of: error))")
            print("❌ Error localized description: \(error.localizedDescription)")

            // Try to extract more details from the error
            if let nsError = error as NSError? {
                print("❌ NSError domain: \(nsError.domain)")
                print("❌ NSError code: \(nsError.code)")
                print("❌ NSError userInfo: \(nsError.userInfo)")

                // Check if there's response data in userInfo
                if let responseData = nsError.userInfo["responseData"] as? Data {
                    print("❌ Response data: \(String(data: responseData, encoding: .utf8) ?? "Could not decode as UTF-8")")
                }

                // Check for HTTP response details
                if let httpResponse = nsError.userInfo["response"] as? HTTPURLResponse {
                    print("❌ HTTP status code: \(httpResponse.statusCode)")
                    print("❌ HTTP headers: \(httpResponse.allHeaderFields)")
                }
            }

            // Check if it's a DecodableRequestBuilderError
            if let decodableError = error as? DecodableRequestBuilderError {
                print("❌ DecodableRequestBuilderError case: \(decodableError)")
            }

            // Check if it's an ErrorResponse from the generated API client
            if case let ErrorResponse.error(statusCode, data, response, underlyingError) = error {
                print("❌ ErrorResponse.error - Status Code: \(statusCode)")
                print("❌ ErrorResponse.error - Underlying Error: \(underlyingError)")

                if let data = data {
                    print("❌ ErrorResponse.error - Response Data: \(String(data: data, encoding: .utf8) ?? "Could not decode as UTF-8")")

                    // Try to parse as ModelErrorResponse to get structured error info
                    do {
                        let errorResponse = try JSONDecoder().decode(ModelErrorResponse.self, from: data)
                        print("❌ ErrorResponse.error - Parsed ModelErrorResponse: \(errorResponse)")

                        // Use the structured error response to show user-friendly message
                        if let errorCode = errorResponse.errorCode {
                            switch errorCode {
                            case "usagelimitexceedederror":
                                if let details = errorResponse.details?.value as? [String: Any],
                                   let limitType = details["limit_type"] as? String,
                                   let currentUsage = details["current_usage"] as? Int,
                                   let limit = details["limit"] as? Int {

                                    if limitType == "daily_translations" {
                                        errorMessage = "You've reached your daily limit of \(limit) translations. Upgrade to Premium for unlimited translations!"
                                    } else {
                                        errorMessage = "You've reached your \(limitType) limit of \(limit). Current usage: \(currentUsage)."
                                    }
                                } else {
                                    errorMessage = "You've reached your daily translation limit. Upgrade to Premium for unlimited translations!"
                                }

                            case "insufficientcreditserror":
                                errorMessage = "You don't have enough credits to complete this translation. Please upgrade to Premium."

                            case "invalidtokenerror", "tokenexpirederror":
                                errorMessage = "Your session has expired. Please sign in again."

                            case "invalidinputerror":
                                errorMessage = "The text you entered is invalid. Please check and try again."

                            case "servicenotavailableerror":
                                errorMessage = "Translation service is temporarily unavailable. Please try again later."

                            default:
                                errorMessage = errorResponse.message ?? error.localizedDescription
                            }
                        } else {
                            errorMessage = errorResponse.message ?? error.localizedDescription
                        }

                        // Don't set errorMessage again below since we set it above
                        return

                    } catch {
                        print("❌ ErrorResponse.error - Could not parse as ModelErrorResponse: \(error)")

                        // Fallback: try to parse as generic JSON
                        do {
                            if let jsonObject = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                                print("❌ ErrorResponse.error - Parsed JSON: \(jsonObject)")
                            }
                        } catch {
                            print("❌ ErrorResponse.error - Could not parse JSON: \(error)")
                        }
                    }
                } else {
                    print("❌ ErrorResponse.error - No response data")
                }

                if let response = response {
                    print("❌ ErrorResponse.error - URL Response: \(response)")
                }
            }

            errorMessage = error.localizedDescription
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
                Text(translation.direction == .genzToStandard ? "Gen Z:" : "English:")
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
                Text(translation.direction == .genzToStandard ? "English:" : "Gen Z:")
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
