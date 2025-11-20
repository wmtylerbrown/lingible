import SwiftUI
import LingibleAPI

struct QuizActiveView: View {
    @ObservedObject var viewModel: QuizViewModel
    @EnvironmentObject var appCoordinator: AppCoordinator
    @State private var showExitConfirmation: Bool = false

    private var userTier: UsageResponse.Tier {
        appCoordinator.userUsage?.tier ?? .free
    }

    var body: some View {
        ZStack {
            Color.lingibleBackground
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Header with upgrade button
                        EnhancedHeader.logoOnly(
                            userTier: userTier,
                            onUpgradeTap: {
                                if userTier == .free {
                                    viewModel.showingUpgradePrompt = true
                                }
                            }
                        )

                // Banner Ad (for free users only)
                if let adManager = appCoordinator.adManager, adManager.shouldShowBanner {
                    adManager.createBannerAdView()
                        .padding(.horizontal, 20)
                        .padding(.bottom, 10)
                }

                // Simplified Progress Tracker (question number only)
                simplifiedProgressTracker
                    .padding(.horizontal, 20)
                    .padding(.vertical, 8)

                // Interstitial view (between questions)
                if viewModel.showingInterstitial {
                    QuizInterstitialView()
                        .transition(.opacity)
                        .zIndex(1)
                }

                // Question Card (one at a time)
                if !viewModel.showingInterstitial {
                    if let currentQuestion = viewModel.currentQuestion {
                        QuizQuestionCardView(
                            question: currentQuestion,
                            questionNumber: viewModel.questionsAnswered + 1,
                            viewModel: viewModel
                        )
                        .id(currentQuestion.questionId) // Force redraw on question change
                        .transition(.asymmetric(insertion: .move(edge: .trailing), removal: .move(edge: .leading)))
                        .animation(.easeInOut, value: viewModel.questionsAnswered)
                    } else {
                        VStack {
                            ProgressView()
                            Text("Loading question...")
                                .foregroundColor(.secondary)
                                .padding()
                        }
                    }
                }

                Spacer()
            }
        }
        .navigationBarHidden(true)
        .alert("Exit Quiz?", isPresented: $showExitConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Exit", role: .destructive) {
                Task {
                    await viewModel.endQuiz()
                }
            }
        } message: {
            if let progress = viewModel.sessionProgress {
                Text("You've answered \(progress.questionsAnswered) questions with a score of \(Int(progress.totalScore)) points and \(Int(progress.accuracy * 100))% accuracy.")
            } else {
                Text("Are you sure you want to exit? Your progress will be saved.")
            }
        }
        .sheet(isPresented: $viewModel.showingUpgradePrompt) {
            UpgradePromptView(
                translationCount: nil,
                onUpgrade: {},
                onDismiss: { viewModel.showingUpgradePrompt = false },
                userUsage: appCoordinator.userUsage
            )
        }
    }

    // MARK: - Simplified Progress Tracker
    private var simplifiedProgressTracker: some View {
        HStack {
            if viewModel.sessionProgress != nil {
                Text("Question \(viewModel.questionsAnswered + 1)")
                    .font(.headline)
                    .fontWeight(.semibold)
                    .foregroundColor(.lingiblePrimary)
            } else {
                HStack(spacing: 8) {
                    ProgressView()
                        .scaleEffect(0.8)
                    Text("Starting quiz...")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            Spacer()
            Button(action: {
                showExitConfirmation = true
            }) {
                Text("Exit")
                    .font(.subheadline)
                    .foregroundColor(.red)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color(.label).opacity(0.05), radius: 2, x: 0, y: 1)
    }

}
