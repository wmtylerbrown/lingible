import SwiftUI
import Combine
import LingibleAPI
import Amplify

// MARK: - Trending View
struct TrendingView: View {
    @StateObject private var viewModel: TrendingViewModel
    @State private var showingUpgradePrompt = false
    @EnvironmentObject var appCoordinator: AppCoordinator

    init(
        trendingService: TrendingServiceProtocol,
        userService: any UserServiceProtocol,
        authenticationService: AuthenticationServiceProtocol
    ) {
        self._viewModel = StateObject(wrappedValue: TrendingViewModel(
            trendingService: trendingService,
            userService: userService,
            authenticationService: authenticationService
        ))
    }

    var body: some View {
        NavigationView {
            ZStack {
                Color.lingibleBackground
                    .ignoresSafeArea()

                VStack(spacing: 0) {
                    // Header
                    CommonHeader.withRefresh(isLoading: viewModel.isLoading) {
                        Task {
                            await viewModel.refreshTrendingTerms()
                        }
                    }

                    // Banner Ad (for free users only)
                    if appCoordinator.adManager.shouldShowBanner {
                        appCoordinator.adManager.createBannerAdView()
                            .padding(.horizontal, 20)
                            .padding(.bottom, 10)
                    }

                    // Category filter for premium users
                    if viewModel.userTier == .premium {
                        categoryFilterView
                    }

                    // Main content
                    if viewModel.isLoading {
                        loadingView
                    } else if viewModel.hasError {
                        errorView
                    } else if viewModel.trendingTerms.isEmpty {
                        emptyStateView
                    } else {
                        trendingTermsList
                    }
                }
            }
            .navigationBarHidden(true)
            .refreshable {
                await viewModel.refreshTrendingTerms()
            }
            .onAppear {
                Task {
                    await viewModel.loadTrendingTerms()
                }
            }
            .sheet(isPresented: $showingUpgradePrompt) {
                UpgradePromptView(
                    translationCount: appCoordinator.userUsage?.dailyUsed ?? 0,
                    onUpgrade: { showingUpgradePrompt = false },
                    onDismiss: { showingUpgradePrompt = false },
                    userUsage: appCoordinator.userUsage
                )
            }
        }
    }

    // MARK: - Category Filter View
    private var categoryFilterView: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                // All categories button
                CategoryButton(
                    title: "All",
                    icon: "list.bullet",
                    isSelected: viewModel.selectedCategory == nil
                ) {
                    viewModel.selectCategory(nil)
                }

                // Category buttons
                ForEach(viewModel.availableCategories, id: \.self) { category in
                    CategoryButton(
                        title: category.displayName,
                        icon: category.icon,
                        isSelected: viewModel.selectedCategory == category
                    ) {
                        viewModel.selectCategory(category)
                    }
                }
            }
            .padding(.horizontal, 16)
        }
        .padding(.vertical, 8)
        .background(Color(.systemGroupedBackground))
    }

    // MARK: - Trending Terms List
    private var trendingTermsList: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                // Header with stats
                if viewModel.userTier == .premium {
                    statsHeaderView
                }

                // Trending terms
                ForEach(viewModel.trendingTerms, id: \.term) { term in
                    TrendingTermCard(
                        term: term,
                        userTier: viewModel.userTier
                    )
                    .onTapGesture {
                        if term.hasPremiumContent && viewModel.userTier == .free {
                            showingUpgradePrompt = true
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
    }

    // MARK: - Stats Header View
    private var statsHeaderView: some View {
        VStack(spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("\(viewModel.totalCount) trending terms")
                        .font(.headline)
                        .fontWeight(.semibold)

                    if let lastUpdated = viewModel.lastUpdated {
                        Text("Updated \(lastUpdated, style: .relative) ago")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                if let category = viewModel.selectedCategory {
                    HStack(spacing: 4) {
                        Image(systemName: category.icon)
                            .foregroundColor(.lingiblePrimary)
                        Text(category.displayName)
                            .font(.caption)
                            .fontWeight(.medium)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(8)
                }
            }
        }
        .padding(16)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color(.label).opacity(0.05), radius: 2, x: 0, y: 1)
    }

    // MARK: - Loading View
    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)

            Text("Loading trending terms...")
                .font(.body)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Error View
    private var errorView: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.orange)

            Text("Something went wrong")
                .font(.headline)
                .fontWeight(.semibold)

            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            Button("Try Again") {
                Task {
                    await viewModel.loadTrendingTerms()
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Empty State View
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 48))
                .foregroundColor(.lingiblePrimary)

            Text("No trending terms found")
                .font(.headline)
                .fontWeight(.semibold)

            Text("Check back later for the latest trending GenZ slang!")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button("Refresh") {
                Task {
                    await viewModel.refreshTrendingTerms()
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Category Button
struct CategoryButton: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)

                Text(title)
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                isSelected ? Color.lingiblePrimary : Color(.systemBackground)
            )
            .foregroundColor(
                isSelected ? .white : .primary
            )
            .cornerRadius(20)
            .overlay(
                RoundedRectangle(cornerRadius: 20)
                    .stroke(Color.lingiblePrimary, lineWidth: isSelected ? 0 : 1)
            )
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - Preview
#Preview {
    TrendingView(
        trendingService: TrendingService(authenticationService: AuthenticationService()),
        userService: UserService(authenticationService: AuthenticationService()),
        authenticationService: AuthenticationService()
    )
}
