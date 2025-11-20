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
    @State private var upgradePromptCount = 0
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
                    // Header with upgrade button
                    EnhancedHeader.logoOnly(
                        userTier: userTier,
                        onUpgradeTap: {
                            // Only show upgrade prompt for free users
                            if userTier == .free {
                                showingUpgradePrompt = true
                            }
                        }
                    )

                    // Banner Ad (for free users only)
                    if let adManager = appCoordinator.adManager, adManager.shouldShowBanner {
                        adManager.createBannerAdView()
                            .padding(.horizontal, 20)
                            .padding(.bottom, 10)
                    }

                    // Scrollable content area
                    ScrollView {
                        VStack(spacing: 20) {
                            // Input card
                            if showInputCard {
                                inputCardView
                                    .padding(.horizontal, 20)
                                    .animation(.spring(response: 0.6, dampingFraction: 0.8), value: showInputCard)
                            }

                            // Current result (if any)
                            if let currentResult = currentTranslationResult {
                                currentResultCardView(translation: currentResult)
                                    .padding(.horizontal, 20)
                                    .animation(.spring(response: 0.6, dampingFraction: 0.8), value: showInputCard)
                            }

                            // Translation history
                            if !translationHistory.isEmpty {
                                translationHistoryView
                            }
                        }
                        .padding(.top, 20)
                        .padding(.bottom, 100) // Extra padding for better scrolling
                    }
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
                    translationCount: upgradePromptCount > 0 ? upgradePromptCount : (appCoordinator.userUsage?.dailyUsed ?? 0),
                    onUpgrade: {
                        showingUpgradePrompt = false
                        // Refresh user data after successful upgrade
                        Task {
                            await appCoordinator.userService.refreshUserData()
                        }
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
                .frame(minHeight: 120, maxHeight: 300)
                .fixedSize(horizontal: false, vertical: true)
                .padding(12)
                .background(Color(.systemBackground))
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
        .background(Color(.systemBackground))
        .cornerRadius(20)
        .shadow(color: Color(.label).opacity(0.1), radius: 10, x: 0, y: 5)
    }

    // MARK: - Current Result Card View
    private func currentResultCardView(translation: TranslationHistoryItem) -> some View {
        VStack(spacing: 16) {
            // Compact header with new translation button
            HStack {
                HStack(spacing: 6) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.subheadline)
                        .foregroundColor(.green)

                    Text("Just translated")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button(action: handleNewButtonTap) {
                    HStack(spacing: 4) {
                        Image(systemName: "plus.circle.fill")
                            .font(.subheadline)

                        Text("New")
                            .font(.subheadline)
                            .fontWeight(.medium)
                    }
                    .foregroundColor(.lingiblePrimary)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(12)
                }
            }

            // Original text
            VStack(alignment: .leading, spacing: 6) {
                Text(translation.direction == .genzToStandard ? "Gen Z:" : "English:")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.originalText)
                    .font(.body)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(12)
                    .background(Color.lingibleSecondary.opacity(0.1))
                    .cornerRadius(8)
            }

            // Translated text
            VStack(alignment: .leading, spacing: 6) {
                Text(translation.direction == .genzToStandard ? "English:" : "Gen Z:")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.translatedText)
                    .font(.body)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(12)
                    .background(Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(8)
            }
        }
        .padding(20)
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: Color(.label).opacity(0.08), radius: 8, x: 0, y: 4)
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

            LazyVStack(spacing: 16) {
                ForEach(translationHistory) { translation in
                    TranslationResultCard(translation: translation)
                }
            }
            .padding(.horizontal, 20)
        }
    }

    // MARK: - Actions
    private func handleNewButtonTap() {
        // Check if we should show an interstitial ad when opening new translation
        if userTier == .free, let adManager = appCoordinator.adManager {
            adManager.checkAndShowInterstitialAdForNewTranslation()
        }

        // If we have a current result, move it to history
        if let currentResult = currentTranslationResult {
            translationHistory.insert(currentResult, at: 0)

            // Keep only last 5 translations for performance
            if translationHistory.count > 5 {
                translationHistory = Array(translationHistory.prefix(5))
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

        // Check if user has exceeded daily limit
        let currentUsage = appCoordinator.userUsage?.dailyUsed ?? 0
        let dailyLimit = appCoordinator.userUsage?.dailyLimit ?? 10

        if userTier == .free && currentUsage >= dailyLimit {
            // Show upgrade prompt when daily limit reached (block translation)
            upgradePromptCount = currentUsage
            showingUpgradePrompt = true
            return
        }

        // Dismiss keyboard
        isInputFocused = false

        Task {
            await performTranslation(text: inputText)
        }
    }

    private func showUpgradePrompt() {
        // Show upgrade prompt instead of error message
        upgradePromptCount = appCoordinator.userUsage?.dailyUsed ?? 0
        showingUpgradePrompt = true
    }

    private func performTranslation(text: String) async {
        isLoading = true
        errorMessage = nil

        do {
            // Get current user from the shared authentication service
            guard try await getCurrentUser() != nil else {
                errorMessage = "You need to sign in to translate text"
                isLoading = false
                return
            }

            // Get the JWT token using the centralized auth service
            let accessToken = try await appCoordinator.authenticationService.getAuthToken()

            // Configure API client with auth token
            let authHeader = "Bearer \(accessToken)"
            LingibleAPIAPI.customHeaders["Authorization"] = authHeader

            // Create translation request using the generated API
            let request = TranslationRequest(
                text: text,
                direction: isGenZToEnglish ? .genzToEnglish : .englishToGenz
            )

            // Make API call
            let response = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<TranslationResponse, Error>) in
                TranslationAPI.translatePost(translationRequest: request) { data, error in
                    if let error = error {
                        continuation.resume(throwing: error)
                    } else if let data = data {
                        continuation.resume(returning: data)
                    } else {
                        continuation.resume(throwing: NSError(domain: "TranslationError", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"]))
                    }
                }
            }

            // Create history item
            let historyItem = TranslationHistoryItem(
                id: UUID().uuidString,
                originalText: text,
                translatedText: response.translatedText,
                createdAt: Date(),
                direction: isGenZToEnglish ? .genzToStandard : .standardToGenz
            )

            // Set as current result and hide input card
            currentTranslationResult = historyItem
            withAnimation(.spring()) {
                showInputCard = false
            }

            // Update user usage data with the response from backend
            appCoordinator.userService.updateUsageFromTranslation(
                dailyUsed: response.dailyUsed,
                dailyLimit: response.dailyLimit,
                tier: response.tier.toAppTier()
            )

            // Update AdManager with new translation count (only for free users)
            if let adManager = appCoordinator.adManager {
                adManager.updateAdVisibility()
            }

            DispatchQueue.main.async {
                // Make sure we're still in the authenticated state
                if appCoordinator.currentState != .authenticated {
                    appCoordinator.restoreAuthenticatedState()
                }

                // Ensure the translation result is still visible
                if currentTranslationResult == nil {
                    showInputCard = false
                }
            }

            // Daily limit check is now handled in translate() function before API call

        } catch {

            // Check if it's an ErrorResponse from the generated API client
            if case let ErrorResponse.error(_, data, _, _) = error {
                if let data = data {
                    // Try to parse as ModelErrorResponse to get structured error info
                    do {
                        let decoder = JSONDecoder()
                        decoder.dateDecodingStrategy = .iso8601
                        let errorResponse = try decoder.decode(ModelErrorResponse.self, from: data)

                        // Use the structured error response to show user-friendly message
                        let errorCode = errorResponse.errorCode
                        switch errorCode {
                            case "usagelimitexceedederror":
                                if let details = errorResponse.details?.value as? [String: Any],
                                   let limitType = details["limit_type"] as? String,
                                   let currentUsage = details["current_usage"] as? Int,
                                   let limit = details["limit"] as? Int {

                                    if limitType == "daily_translations" {
                                        // Show upgrade prompt instead of error message
                                        upgradePromptCount = currentUsage
                                        DispatchQueue.main.async {
                                            showingUpgradePrompt = true
                                        }
                                        return // Don't set errorMessage
                                    } else {
                                        errorMessage = "You've reached your \(limitType) limit of \(limit). Current usage: \(currentUsage)."
                                    }
                                } else {
                                    // Show upgrade prompt for daily limit (use dynamic limit)
                                    let dailyLimit = appCoordinator.userUsage?.dailyLimit ?? 10
                                    upgradePromptCount = dailyLimit
                                    DispatchQueue.main.async {
                                        showingUpgradePrompt = true
                                    }
                                    return // Don't set errorMessage
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
                                errorMessage = errorResponse.message
                        }

                        // Don't set errorMessage again below since we set it above
                        return

                    } catch {
                        // Fallback to generic error message
                    }
                }
            }

            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    private func getCurrentUser() async throws -> AuthenticatedUser? {
        // Use the direct method to get the current user value
        if let currentUser = appCoordinator.authenticationService.getCurrentUserValue() {
            return currentUser
        }

        // If no current user, try to check authentication status
        let isAuthenticated = await appCoordinator.authenticationService.checkAuthenticationStatus()

        if isAuthenticated {
            return appCoordinator.authenticationService.getCurrentUserValue()
        }

        return nil
    }

    private func saveCachedTranslations() {
        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            let data = try encoder.encode(translationHistory)
            UserDefaults.standard.set(data, forKey: "cached_translations")
        } catch {
            // Log error but continue without caching
            print("Failed to save cached translations: \(error.localizedDescription)")
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
            // Log error but continue without cached data
            print("Failed to load cached translations: \(error.localizedDescription)")
        }
    }
}

// MARK: - API Tier Extension
extension TranslationResponse.Tier {
    func toAppTier() -> UserTier {
        switch self {
        case .free:
            return .free
        case .premium:
            return .premium
        }
    }
}

// MARK: - Translation Result Card
struct TranslationResultCard: View {
    let translation: TranslationHistoryItem

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Compact header
            HStack {
                HStack(spacing: 6) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.subheadline)
                        .foregroundColor(.green)

                    Text("Translation")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Text(translation.createdAt, style: .time)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            // Original text
            VStack(alignment: .leading, spacing: 6) {
                Text(translation.direction == .genzToStandard ? "Gen Z:" : "English:")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.originalText)
                    .font(.body)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(12)
                    .background(Color.lingibleSecondary.opacity(0.1))
                    .cornerRadius(8)
            }

            // Translated text
            VStack(alignment: .leading, spacing: 6) {
                Text(translation.direction == .genzToStandard ? "English:" : "Gen Z:")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.translatedText)
                    .font(.body)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(12)
                    .background(Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(8)
            }
        }
        .padding(16)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color(.label).opacity(0.06), radius: 6, x: 0, y: 3)
    }
}

#Preview {
    TranslationView()
        .environmentObject(AppCoordinator())
}
