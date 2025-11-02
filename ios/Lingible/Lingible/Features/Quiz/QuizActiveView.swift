import SwiftUI
import LingibleAPI

struct QuizActiveView: View {
    @ObservedObject var viewModel: QuizViewModel
    @State private var showExitConfirmation: Bool = false

    var body: some View {
        ZStack {
            Color.lingibleBackground
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Progress Tracker at Top
                progressTracker

                // Question Card (one at a time)
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

                Spacer()
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button("Exit") {
                    showExitConfirmation = true
                }
            }
        }
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
    }

    // MARK: - Progress Tracker
    private var progressTracker: some View {
        VStack(spacing: 8) {
            if let progress = viewModel.sessionProgress {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Image(systemName: "questionmark.circle.fill")
                                .foregroundColor(.lingiblePrimary)
                            Text("Questions: \(progress.questionsAnswered)")
                                .font(.subheadline)
                                .fontWeight(.medium)
                        }
                        HStack {
                            Image(systemName: "star.fill")
                                .foregroundColor(.yellow)
                            Text("Score: \(Int(progress.totalScore))")
                                .font(.subheadline)
                                .fontWeight(.medium)
                        }
                    }

                    Spacer()

                    VStack(alignment: .trailing, spacing: 4) {
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                            Text("Correct: \(progress.correctCount)")
                                .font(.subheadline)
                                .fontWeight(.medium)
                        }
                        HStack {
                            Image(systemName: "percent")
                                .foregroundColor(.blue)
                            Text("Accuracy: \(Int(progress.accuracy * 100))%")
                                .font(.subheadline)
                                .fontWeight(.medium)
                        }
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 12)

                if progress.timeSpentSeconds > 0 {
                    HStack {
                        Image(systemName: "clock.fill")
                            .foregroundColor(.secondary)
                        Text("Time: \(formatTime(TimeInterval(progress.timeSpentSeconds)))")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Spacer()
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 8)
                }
            } else {
                // Loading state
                HStack {
                    ProgressView()
                        .scaleEffect(0.8)
                    Text("Starting quiz...")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .padding()
            }
        }
        .background(Color(.systemBackground))
        .shadow(color: Color(.label).opacity(0.05), radius: 2, x: 0, y: 1)
    }

    private func formatTime(_ timeInterval: TimeInterval) -> String {
        let seconds = Int(timeInterval)
        let minutes = seconds / 60
        let remainingSeconds = seconds % 60

        if minutes > 0 {
            return String(format: "%d:%02d", minutes, remainingSeconds)
        } else {
            return String(format: "%ds", remainingSeconds)
        }
    }
}
