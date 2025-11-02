import SwiftUI
import LingibleAPI

struct QuizResultsView: View {
    @ObservedObject var viewModel: QuizViewModel
    @State private var showingShareSheet = false

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                if let result = viewModel.quizResult {
                    // Score Display
                    scoreDisplay(result: result)

                    // Time Bonus Breakdown
                    timeBonusBreakdown(result: result)

                    // Per-Question Results
                    perQuestionResults(results: result.results)

                    // Action Buttons
                    actionButtons
                } else {
                    ProgressView("Loading results...")
                }
            }
            .padding()
        }
        .navigationTitle("Quiz Results")
        .navigationBarTitleDisplayMode(.inline)
        .background(Color.lingibleBackground)
        .sheet(isPresented: $showingShareSheet) {
            if let shareText = viewModel.quizResult?.shareText {
                ShareSheet(activityItems: [shareText])
            }
        }
    }

    // MARK: - Score Display
    private func scoreDisplay(result: QuizResult) -> some View {
        VStack(spacing: 12) {
            Text("Your Score")
                .font(.headline)
                .foregroundColor(.secondary)

            Text("\(result.score)/\(result.totalPossible)")
                .font(.system(size: 56, weight: .bold))
                .foregroundColor(.lingiblePrimary)

            let accuracy = Int((Double(result.correctCount) / Double(result.totalQuestions)) * 100)
            Text("\(accuracy)% Accuracy")
                .font(.title3)
                .foregroundColor(.secondary)

            // Gen Z messaging based on score
            Text(getScoreMessage(accuracy: accuracy))
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(.primary)
                .multilineTextAlignment(.center)
                .padding()
                .background(messageBackgroundColor(accuracy: accuracy))
                .cornerRadius(12)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: Color(.label).opacity(0.1), radius: 8, x: 0, y: 4)
    }

    // MARK: - Time Bonus Breakdown
    private func timeBonusBreakdown(result: QuizResult) -> some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "bolt.fill")
                    .foregroundColor(.yellow)
                    .font(.title2)
                Text("Time Bonus Breakdown")
                    .font(.headline)
                    .foregroundColor(.primary)
                Spacer()
            }

            Divider()

            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Base Score")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Text("\(result.score - result.timeBonusPoints) points")
                        .font(.title3)
                        .fontWeight(.semibold)
                        .foregroundColor(.primary)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text("Time Bonus")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Text("+\(result.timeBonusPoints) points")
                        .font(.title3)
                        .fontWeight(.bold)
                        .foregroundColor(.yellow)
                }
            }

            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Time Taken")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(formatTime(TimeInterval(result.timeTakenSeconds)))
                        .font(.subheadline)
                        .foregroundColor(.primary)
                }

                Spacer()

                if let challenge = viewModel.currentChallenge {
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("Time Limit")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text(formatTime(TimeInterval(challenge.timeLimitSeconds)))
                            .font(.subheadline)
                            .foregroundColor(.primary)
                    }
                }
            }
            .padding(.top, 4)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.yellow.opacity(0.3), lineWidth: 2)
        )
    }

    // MARK: - Per-Question Results
    private func perQuestionResults(results: [QuizQuestionResult]) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Question Breakdown")
                .font(.headline)
                .foregroundColor(.primary)

            ForEach(results, id: \.questionId) { result in
                questionResultCard(result: result)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
    }

    private func questionResultCard(result: QuizQuestionResult) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("'\(result.slangTerm)'")
                    .font(.headline)
                    .foregroundColor(.lingiblePrimary)

                Spacer()

                if result.isCorrect {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                        .font(.title2)
                } else {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.red)
                        .font(.title2)
                }
            }

            HStack {
                Text("Your answer:")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(result.yourAnswer.uppercased())
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(.primary)
            }

            if !result.isCorrect {
                HStack {
                    Text("Correct answer:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(result.correctAnswer.uppercased())
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.green)
                }
            }

            if !result.explanation.isEmpty {
                Text(result.explanation)
                    .font(.body)
                    .foregroundColor(.secondary)
                    .padding(.top, 4)
            }
        }
        .padding()
        .background(result.isCorrect ? Color.green.opacity(0.1) : Color.red.opacity(0.1))
        .cornerRadius(8)
    }

    // MARK: - Action Buttons
    private var actionButtons: some View {
        VStack(spacing: 12) {
            Button(action: {
                showingShareSheet = true
            }) {
                HStack {
                    Image(systemName: "square.and.arrow.up")
                    Text("Share Results")
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.lingiblePrimary)
                .foregroundColor(.white)
                .cornerRadius(12)
            }

            Button(action: {
                viewModel.returnToLobby()
            }) {
                HStack {
                    Image(systemName: "arrow.counterclockwise")
                    Text("Play Again")
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color(.systemGray5))
                .foregroundColor(.primary)
                .cornerRadius(12)
            }
        }
    }

    // MARK: - Helper Methods
    private func getScoreMessage(accuracy: Int) -> String {
        switch accuracy {
        case 90...100:
            return "You're the GOAT! Peak Gen Z knowledge 🔥"
        case 70..<90:
            return "You got the sauce! Nice work 💯"
        case 50..<70:
            return "Not bad, but you can do better 💪"
        default:
            return "Keep learning, you'll get there! 📚"
        }
    }

    private func messageBackgroundColor(accuracy: Int) -> Color {
        switch accuracy {
        case 90...100:
            return Color.green.opacity(0.1)
        case 70..<90:
            return Color.blue.opacity(0.1)
        case 50..<70:
            return Color.orange.opacity(0.1)
        default:
            return Color.red.opacity(0.1)
        }
    }

    private func formatTime(_ timeInterval: TimeInterval) -> String {
        let seconds = Int(timeInterval)
        let minutes = seconds / 60
        let remainingSeconds = seconds % 60

        if minutes > 0 {
            return String(format: "%dm %ds", minutes, remainingSeconds)
        } else {
            return String(format: "%ds", remainingSeconds)
        }
    }
}

// MARK: - Share Sheet
struct ShareSheet: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = UIActivityViewController(
            activityItems: activityItems,
            applicationActivities: nil
        )
        return controller
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
