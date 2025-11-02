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

                    // Stats Breakdown
                    statsBreakdown(result: result)

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

            Text("\(formatScore(result.score))")
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

    // MARK: - Stats Breakdown
    private func statsBreakdown(result: QuizResult) -> some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "chart.bar.fill")
                    .foregroundColor(.lingiblePrimary)
                    .font(.title2)
                Text("Quiz Statistics")
                    .font(.headline)
                    .foregroundColor(.primary)
                Spacer()
            }

            Divider()

            HStack(spacing: 20) {
                VStack(spacing: 4) {
                    Text("\(result.correctCount)")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.green)
                    Text("Correct")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                VStack(spacing: 4) {
                    Text("\(result.totalQuestions - result.correctCount)")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.red)
                    Text("Incorrect")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                VStack(spacing: 4) {
                    Text(formatTime(TimeInterval(result.timeTakenSeconds)))
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                    Text("Time")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.vertical, 8)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color(.label).opacity(0.1), radius: 8, x: 0, y: 4)
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

    private func formatScore(_ score: Float) -> String {
        // Round to whole number
        return String(format: "%.0f", score.rounded())
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
