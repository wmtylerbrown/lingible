import SwiftUI
import LingibleAPI

struct QuizLobbyView: View {
    @ObservedObject var viewModel: QuizViewModel
    @State private var selectedDifficulty: QuizDifficulty = .beginner
    @State private var selectedQuestionCount: Int = 10

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Stats Card
                    if let history = viewModel.quizHistory {
                        statsCard(history: history)
                    }

                    // Quiz Configuration
                    configurationCard

                    // Start Quiz Button
                    startQuizButton

                    // Error Message
                    if let errorMessage = viewModel.errorMessage {
                        errorCard(message: errorMessage)
                    }
                }
                .padding()
            }
            .navigationTitle("Quiz")
            .background(Color.lingibleBackground)
            .onAppear {
                Task {
                    await viewModel.loadQuizHistory()
                }
            }
        }
    }

    // MARK: - Stats Card
    private func statsCard(history: QuizHistory) -> some View {
        VStack(spacing: 16) {
            Text("Your Stats")
                .font(.headline)
                .foregroundColor(.primary)

            HStack(spacing: 20) {
                statItem(title: "Quizzes", value: "\(history.totalQuizzes)")
                statItem(title: "Best Score", value: "\(history.bestScore)")
                statItem(title: "Avg Score", value: String(format: "%.0f", history.averageScore))
                statItem(title: "Accuracy", value: String(format: "%.0f%%", history.accuracyRate))
            }

            Divider()

            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Today: \(history.quizzesToday)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    if !history.canTakeQuiz, let reason = history.reason {
                        Text(reason)
                            .font(.caption)
                            .foregroundColor(.orange)
                    }
                }
                Spacer()
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color(.label).opacity(0.05), radius: 2, x: 0, y: 1)
    }

    private func statItem(title: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(.lingiblePrimary)
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Configuration Card
    private var configurationCard: some View {
        VStack(spacing: 16) {
            Text("Ready to test your Gen Z slang? No cap.")
                .font(.headline)
                .foregroundColor(.primary)
                .multilineTextAlignment(.center)

            // Difficulty Selector
            VStack(alignment: .leading, spacing: 8) {
                Text("Difficulty")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Picker("Difficulty", selection: $selectedDifficulty) {
                    Text("Beginner").tag(QuizDifficulty.beginner)
                    Text("Intermediate").tag(QuizDifficulty.intermediate)
                    Text("Advanced").tag(QuizDifficulty.advanced)
                }
                .pickerStyle(SegmentedPickerStyle())
            }

            // Question Count Selector
            VStack(alignment: .leading, spacing: 8) {
                Text("Number of Questions")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Picker("Question Count", selection: $selectedQuestionCount) {
                    Text("5").tag(5)
                    Text("10").tag(10)
                    Text("15").tag(15)
                }
                .pickerStyle(SegmentedPickerStyle())
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color(.label).opacity(0.05), radius: 2, x: 0, y: 1)
    }

    // MARK: - Start Quiz Button
    private var startQuizButton: some View {
        Button(action: {
            Task {
                await viewModel.startQuiz(difficulty: selectedDifficulty, questionCount: selectedQuestionCount)
            }
        }) {
            HStack {
                if viewModel.isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.8)
                } else {
                    Image(systemName: "play.fill")
                }
                Text(viewModel.isLoading ? "Starting Quiz..." : "Start Quiz")
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(viewModel.canStartQuiz ? Color.lingiblePrimary : Color.gray)
            .foregroundColor(.white)
            .cornerRadius(12)
        }
        .disabled(!viewModel.canStartQuiz || viewModel.isLoading)
    }

    private var canStartQuiz: Bool {
        viewModel.quizHistory?.canTakeQuiz ?? false
    }

    // MARK: - Error Card
    private func errorCard(message: String) -> some View {
        HStack {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.orange)
            Text(message)
                .font(.subheadline)
                .foregroundColor(.primary)
            Spacer()
        }
        .padding()
        .background(Color.orange.opacity(0.1))
        .cornerRadius(8)
    }
}

// MARK: - ViewModel Extension
extension QuizViewModel {
    var canStartQuiz: Bool {
        quizHistory?.canTakeQuiz ?? false
    }
}
