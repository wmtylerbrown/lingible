import SwiftUI
import LingibleAPI

struct QuizActiveView: View {
    @ObservedObject var viewModel: QuizViewModel
    @State private var quizStartTime: Date?
    @State private var totalElapsedTime: TimeInterval = 0
    @State private var estimatedBonus: Int = 0

    var body: some View {
        ZStack {
            Color.lingibleBackground
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Time Bonus Tracker at Top
                timeBonusTracker

                // Question Card (one at a time)
                if let currentQuestion = viewModel.currentQuestion {
                    QuizQuestionCardView(
                        question: currentQuestion,
                        questionNumber: viewModel.currentQuestionIndex + 1,
                        totalQuestions: viewModel.totalQuestions,
                        viewModel: viewModel
                    )
                    .id(currentQuestion.questionId) // Force redraw on question change
                    .transition(.asymmetric(insertion: .move(edge: .trailing), removal: .move(edge: .leading)))
                    .animation(.easeInOut, value: viewModel.currentQuestionIndex)
                } else {
                    VStack {
                        ProgressView()
                        Text("Loading question...")
                            .foregroundColor(.secondary)
                            .padding()
                    }
                }

                // Submit Button
                submitButton
            }
        }
        .onAppear {
            quizStartTime = Date()
            startTimeTracking()
        }
        .onChange(of: viewModel.allQuestionsAnswered) {
            if viewModel.allQuestionsAnswered {
                updateEstimatedBonus()
            }
        }
    }

    // MARK: - Time Bonus Tracker
    private var timeBonusTracker: some View {
        VStack(spacing: 8) {
            HStack {
                Image(systemName: "clock.fill")
                    .foregroundColor(.lingiblePrimary)
                Text(formatTime(totalElapsedTime))
                    .font(.headline)
                    .fontWeight(.semibold)
                    .foregroundColor(.primary)

                Spacer()

                if let challenge = viewModel.currentChallenge {
                    Text("Limit: \(formatTime(TimeInterval(challenge.timeLimitSeconds)))")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal)
            .padding(.top)

            // Estimated Bonus
            if estimatedBonus > 0 {
                HStack {
                    Image(systemName: "bolt.fill")
                        .foregroundColor(.yellow)
                    Text("Current pace: +\(estimatedBonus) bonus points")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.primary)
                    Spacer()
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
                .background(Color.yellow.opacity(0.1))
            }
        }
        .background(Color(.systemBackground))
        .shadow(color: Color(.label).opacity(0.05), radius: 2, x: 0, y: 1)
    }

    // MARK: - Submit Button
    private var submitButton: some View {
        Button(action: {
            Task {
                await viewModel.submitQuiz()
            }
        }) {
            HStack {
                if viewModel.isSubmitting {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.8)
                } else {
                    Image(systemName: "checkmark.circle.fill")
                }
                Text(viewModel.isSubmitting ? "Submitting..." : "Submit Quiz")
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(viewModel.allQuestionsAnswered ? Color.lingiblePrimary : Color.gray)
            .foregroundColor(.white)
            .cornerRadius(12)
        }
        .disabled(!viewModel.allQuestionsAnswered || viewModel.isSubmitting)
        .padding()
        .background(Color(.systemBackground))
        .shadow(color: Color(.label).opacity(0.1), radius: 4, x: 0, y: -2)
    }

    // MARK: - Time Tracking
    private func startTimeTracking() {
        Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
            Task { @MainActor in
                guard let startTime = quizStartTime else { return }
                totalElapsedTime = Date().timeIntervalSince(startTime)
                updateEstimatedBonus()
            }
        }
    }

    private func updateEstimatedBonus() {
        guard let challenge = viewModel.currentChallenge else { return }

        let timeLimit = TimeInterval(challenge.timeLimitSeconds)
        let timeSaved = timeLimit - totalElapsedTime

        if timeSaved > 0 {
            // Backend formula: 1 point per 6 seconds saved, max 10 points
            estimatedBonus = min(10, Int(timeSaved / 6.0))
        } else {
            estimatedBonus = 0
        }
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
