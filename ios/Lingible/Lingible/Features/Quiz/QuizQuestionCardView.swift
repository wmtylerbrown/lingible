import SwiftUI
import LingibleAPI

struct QuizQuestionCardView: View {
    let question: QuizQuestion
    let questionNumber: Int
    @ObservedObject var viewModel: QuizViewModel
    @State private var showContextHint = false
    @State private var timeExpired = false
    @State private var selectedOptionId: String?

    private let questionTimeLimit: Double = 15.0

    var body: some View {
        VStack(spacing: 0) {
            // Timer Bar
            timerBar

            // Question Card
            VStack(spacing: 20) {
                // Question Text
                VStack(spacing: 12) {
                    Text("Question \(questionNumber)")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Text(question.questionText)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.primary)
                        .multilineTextAlignment(.center)

                    // Slang Term Highlight
                    Text("'\(question.slangTerm)'")
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundColor(.lingiblePrimary)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 12)
                        .background(
                            LinearGradient(
                                gradient: Gradient(colors: [
                                    Color.lingiblePrimary.opacity(0.15),
                                    Color.lingiblePrimary.opacity(0.08)
                                ]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.lingiblePrimary.opacity(0.3), lineWidth: 2)
                        )
                }

                // Context Hint (optional)
                if let contextHint = question.contextHint {
                    Button(action: {
                        withAnimation {
                            showContextHint.toggle()
                        }
                    }) {
                        HStack {
                            Image(systemName: showContextHint ? "eye.slash" : "eye")
                            Text(showContextHint ? "Hide Hint" : "Show Hint")
                            Spacer()
                            Image(systemName: showContextHint ? "chevron.up" : "chevron.down")
                        }
                        .font(.subheadline)
                        .foregroundColor(.lingiblePrimary)
                        .padding()
                        .background(Color.lingiblePrimary.opacity(0.1))
                        .cornerRadius(8)
                    }

                    if showContextHint {
                        Text("\"\(contextHint)\"")
                            .font(.body)
                            .italic()
                            .foregroundColor(.secondary)
                            .padding()
                            .background(Color.gray.opacity(0.1))
                            .cornerRadius(8)
                            .transition(.opacity)
                    }
                }

                // Feedback Message (show if we have feedback for current question)
                if let answerResponse = viewModel.lastAnswerResponse {
                    VStack(spacing: 8) {
                        HStack {
                            Image(systemName: answerResponse.isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundColor(answerResponse.isCorrect ? .green : .red)
                            Text(answerResponse.isCorrect ? "Correct! +\(Int(answerResponse.pointsEarned)) points" : "Incorrect")
                                .font(.subheadline)
                                .fontWeight(.semibold)
                                .foregroundColor(answerResponse.isCorrect ? .green : .red)
                        }
                        if !answerResponse.explanation.isEmpty {
                            Text("\(answerResponse.explanation)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .italic()
                        }
                    }
                    .padding()
                    .background(answerResponse.isCorrect ? Color.green.opacity(0.1) : Color.red.opacity(0.1))
                    .cornerRadius(8)
                    .transition(.scale)
                }

                // Time Expired Message
                if timeExpired {
                    Text("That's cap! Time ran out! ⏰")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.orange)
                        .padding()
                        .background(Color.orange.opacity(0.1))
                        .cornerRadius(8)
                        .transition(.scale)
                }

                // Answer Options
                VStack(spacing: 12) {
                    ForEach(question.options, id: \.id) { option in
                        answerButton(option: option)
                    }
                }
            }
            .padding(24)
            .background(
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color(.systemBackground),
                        Color.lingiblePrimary.opacity(0.02)
                    ]),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .cornerRadius(20)
            .shadow(color: Color.lingiblePrimary.opacity(0.15), radius: 12, x: 0, y: 6)
            .shadow(color: Color(.label).opacity(0.05), radius: 4, x: 0, y: 2)
            .padding(.horizontal, 20)
        }
        .onAppear {
            // Check if question timed out
            if viewModel.timedOutQuestions.contains(question.questionId) {
                timeExpired = true
            }

            // Monitor timer expiration
            Task {
                await monitorTimerExpiration()
            }
        }
    }


    // MARK: - Timer Bar
    private var timerBar: some View {
        let timeRemaining = viewModel.getTimeRemaining(questionId: question.questionId)
        let progress = timeRemaining / questionTimeLimit
        let timerColor: Color = {
            if progress > 0.5 {
                return .green
            } else if progress > 0.25 {
                return .yellow
            } else {
                return .red
            }
        }()

        return VStack(spacing: 8) {
            HStack {
                Image(systemName: "clock.fill")
                    .foregroundColor(timerColor)
                Text(String(format: "%.1fs", timeRemaining))
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(timerColor)
                Spacer()
            }
            .padding(.horizontal)

            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 6)

                    Rectangle()
                        .fill(timerColor)
                        .frame(width: geometry.size.width * max(0, progress), height: 6)
                }
            }
            .frame(height: 6)
            .padding(.horizontal)
        }
        .padding(.vertical, 8)
        .background(Color(.systemBackground))
    }

    // MARK: - Answer Button
    private func answerButton(option: QuizOption) -> some View {
        let isSelected = selectedOptionId == option.id || viewModel.lastAnswerResponse != nil
        let isDisabled = selectedOptionId != nil || viewModel.timedOutQuestions.contains(question.questionId) || viewModel.isSubmitting

        return Button(action: {
            if !isDisabled {
                selectedOptionId = option.id
                Task {
                    await viewModel.selectAnswer(questionId: question.questionId, optionId: option.id)
                    // Clear selection after feedback shown
                    try? await Task.sleep(nanoseconds: 1_500_000_000)
                    selectedOptionId = nil
                }
            }
        }) {
            HStack {
                // Option ID (A, B, C, D)
                Text(option.id.uppercased())
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(isSelected ? .white : .lingiblePrimary)
                    .frame(width: 40, height: 40)
                    .background(isSelected ? Color.white.opacity(0.3) : Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(8)

                // Answer Text
                Text(option.text)
                    .font(.body)
                    .foregroundColor(isSelected ? .white : .primary)
                    .multilineTextAlignment(.leading)

                Spacer()

                // Selected indicator
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.white)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                Group {
                    if isSelected {
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color.lingiblePrimary,
                                Color.lingiblePrimary.opacity(0.8)
                            ]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    } else {
                        Color(.systemBackground)
                    }
                }
            )
            .cornerRadius(14)
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(
                        isSelected ? Color.clear : Color.lingiblePrimary.opacity(0.2),
                        lineWidth: 2
                    )
            )
            .shadow(
                color: isSelected ? Color.lingiblePrimary.opacity(0.3) : Color.clear,
                radius: isSelected ? 8 : 0,
                x: 0,
                y: isSelected ? 4 : 0
            )
        }
        .disabled(isDisabled)
        .buttonStyle(PlainButtonStyle())
    }

    // MARK: - Monitor Timer Expiration
    private func monitorTimerExpiration() async {
        // Check every 0.1 seconds if timer expired
        while !timeExpired && viewModel.getTimeRemaining(questionId: question.questionId) > 0 {
            try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

            if viewModel.timedOutQuestions.contains(question.questionId) {
                await MainActor.run {
                    withAnimation {
                        timeExpired = true
                    }
                }
                break
            }
        }
    }
}
