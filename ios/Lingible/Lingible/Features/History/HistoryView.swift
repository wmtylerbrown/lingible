import SwiftUI
import LingibleAPI

struct HistoryView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @StateObject private var historyService: HistoryService
    @Binding var selectedTab: Int
    @State private var translations: [TranslationHistory] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showingClearAlert = false
    @State private var hasMore = false
    @State private var currentOffset = 0
    @State private var isRefreshing = false

    private let pageSize = 20

    init(selectedTab: Binding<Int>) {
        self._selectedTab = selectedTab
        self._historyService = StateObject(wrappedValue: HistoryService())
    }

    init(authenticationService: AuthenticationServiceProtocol, selectedTab: Binding<Int>) {
        self._selectedTab = selectedTab
        self._historyService = StateObject(wrappedValue: HistoryService(authenticationService: authenticationService))
    }

    var body: some View {
        NavigationView {
            ZStack {
                Color.lingibleBackground
                    .ignoresSafeArea()

                VStack(spacing: 0) {
                    // Header
                    CommonHeader.withRefresh(isLoading: isLoading) {
                        Task {
                            await refreshHistory()
                        }
                    }

                    // Title and Clear All button
                    HStack {
                        Text("Translation History")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(.primary)

                        Spacer()

                        if !translations.isEmpty {
                            Button("Clear All") {
                                showingClearAlert = true
                            }
                            .foregroundColor(.red)
                            .font(.body)
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 16)

                    // Main content
                    if isLoading && translations.isEmpty {
                        loadingView
                    } else if translations.isEmpty {
                        emptyStateView
                    } else {
                        translationListView
                    }
                }
            }
            .navigationBarHidden(true)
            .refreshable {
                await refreshHistory()
            }
            .alert("Clear All History", isPresented: $showingClearAlert) {
                Button("Cancel", role: .cancel) { }
                Button("Clear All", role: .destructive) {
                    clearAllHistory()
                }
            } message: {
                Text("This will permanently delete all your translation history. This action cannot be undone.")
            }
            .onAppear {
                loadHistory()
            }
        }
    }

    // MARK: - Views

    private var loadingView: some View {
        VStack(spacing: 20) {
            ProgressView()
                .scaleEffect(1.2)

            Text("Loading translation history...")
                .font(.body)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Image(systemName: "clock.arrow.circlepath")
                .font(.system(size: 60))
                .foregroundColor(.secondary)

            Text("No Translation History")
                .font(.title2)
                .fontWeight(.semibold)
                .foregroundColor(.primary)

            Text("Your translation history will appear here once you start translating text.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Button("Start Translating") {
                // Switch to the translation tab (tag 0)
                selectedTab = 0
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var translationListView: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(translations, id: \.translationId) { translation in
                    TranslationHistoryRow(translation: translation)
                        .onAppear {
                            // Load more when reaching the end
                            if translation == translations.last && hasMore {
                                loadMoreHistory()
                            }
                        }
                }

                if isLoading && !translations.isEmpty {
                    HStack {
                        Spacer()
                        ProgressView()
                            .padding()
                        Spacer()
                    }
                }
            }
            .padding(.horizontal, 20)
        }
    }

    // MARK: - Actions

    private func loadHistory() {
        guard appCoordinator.userUsage?.tier == .premium else {
            errorMessage = "Translation history is only available for premium users."
            return
        }

        isLoading = true
        errorMessage = nil
        currentOffset = 0

        historyService.getTranslationHistory(limit: pageSize, offset: 0) { result in
            DispatchQueue.main.async {
                isLoading = false

                switch result {
                case .success(let response):
                    // Sort translations by created date (most recent first)
                    self.translations = response.translations.sorted { $0.createdAt > $1.createdAt }
                    self.hasMore = response.hasMore
                case .failure(let error):
                    self.errorMessage = "Failed to load history: \(error.localizedDescription)"
                }
            }
        }
    }

    private func loadMoreHistory() {
        guard hasMore && !isLoading else { return }

        isLoading = true
        currentOffset += pageSize

        historyService.getTranslationHistory(limit: pageSize, offset: currentOffset) { result in
            DispatchQueue.main.async {
                isLoading = false

                switch result {
                case .success(let response):
                    // Append new translations and sort by created date (most recent first)
                    self.translations.append(contentsOf: response.translations)
                    self.translations = self.translations.sorted { $0.createdAt > $1.createdAt }
                    self.hasMore = response.hasMore
                case .failure(let error):
                    self.errorMessage = "Failed to load more history: \(error.localizedDescription)"
                }
            }
        }
    }

    private func refreshHistory() async {
        isRefreshing = true
        currentOffset = 0

        historyService.getTranslationHistory(limit: pageSize, offset: 0) { result in
            DispatchQueue.main.async {
                isRefreshing = false

                switch result {
                case .success(let response):
                    // Sort translations by created date (most recent first)
                    self.translations = response.translations.sorted { $0.createdAt > $1.createdAt }
                    self.hasMore = response.hasMore
                case .failure(let error):
                    self.errorMessage = "Failed to refresh history: \(error.localizedDescription)"
                }
            }
        }
    }

    private func clearAllHistory() {
        isLoading = true

        historyService.clearAllHistory { result in
            DispatchQueue.main.async {
                isLoading = false

                switch result {
                case .success:
                    self.translations = []
                    self.hasMore = false
                    self.currentOffset = 0
                case .failure(let error):
                    self.errorMessage = "Failed to clear history: \(error.localizedDescription)"
                }
            }
        }
    }
}

// MARK: - Translation History Row

struct TranslationHistoryRow: View {
    let translation: TranslationHistory

    private var directionIcon: String {
        switch translation.direction {
        case .genzToEnglish:
            return "arrow.right.circle.fill"
        case .englishToGenz:
            return "arrow.left.circle.fill"
        }
    }

    private var directionColor: Color {
        switch translation.direction {
        case .genzToEnglish:
            return .blue
        case .englishToGenz:
            return .purple
        }
    }

    private var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: translation.createdAt)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header with direction and date
            HStack {
                Image(systemName: directionIcon)
                    .foregroundColor(directionColor)
                    .font(.caption)

                Text(directionText)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(directionColor)

                Spacer()

                Text(formattedDate)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            // Original text
            VStack(alignment: .leading, spacing: 4) {
                Text("Original")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(.secondary)

                Text(translation.originalText)
                    .font(.body)
                    .foregroundColor(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            // Arrow
            HStack {
                Spacer()
                Image(systemName: "arrow.down")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
            }

            // Translated text
            VStack(alignment: .leading, spacing: 4) {
                Text("Translation")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(.secondary)

                Text(translation.translatedText)
                    .font(.body)
                    .foregroundColor(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            // Confidence score (if available)
            if let confidence = translation.confidenceScore {
                HStack {
                    Text("Confidence: \(Int(confidence * 100))%")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Spacer()
                }
            }
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 16)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 2, x: 0, y: 1)
    }

    private var directionText: String {
        switch translation.direction {
        case .genzToEnglish:
            return "GenZ → English"
        case .englishToGenz:
            return "English → GenZ"
        }
    }
}

#Preview {
    HistoryView(selectedTab: .constant(0))
        .environmentObject(AppCoordinator())
}
