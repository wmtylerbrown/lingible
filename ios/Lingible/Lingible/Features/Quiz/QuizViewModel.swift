import Foundation
import Combine
import LingibleAPI

// MARK: - Quiz Screen State
enum QuizScreen {
    case lobby
    case active
    case results
}

// MARK: - Quiz ViewModel
@MainActor
final class QuizViewModel: ObservableObject {

    // MARK: - Published Properties
    @Published var quizHistory: QuizHistory?
    @Published var currentChallenge: QuizChallenge?
    @Published var currentQuestionIndex: Int = 0
    @Published var selectedAnswers: [String: String] = [:] // questionId -> optionId
    @Published var questionStartTimes: [String: Date] = [:]
    @Published var questionEndTimes: [String: Date] = [:] // questionId -> completion time
    @Published var questionTimeRemaining: [String: Double] = [:] // questionId -> remaining seconds
    @Published var timedOutQuestions: Set<String> = []
    @Published var isSubmitting: Bool = false
    @Published var quizResult: QuizResult?
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var currentScreen: QuizScreen = .lobby

    // MARK: - Private Properties
    private let quizService: QuizServiceProtocol
    nonisolated(unsafe) private var questionTimers: [String: Timer] = [:]
    private let defaultQuestionTimeLimit: Double = 15.0 // seconds per question

    // MARK: - Computed Properties
    var currentQuestion: QuizQuestion? {
        guard let challenge = currentChallenge,
              currentQuestionIndex < challenge.questions.count else {
            return nil
        }
        return challenge.questions[currentQuestionIndex]
    }

    var totalQuestions: Int {
        currentChallenge?.questions.count ?? 0
    }

    var progress: Double {
        guard totalQuestions > 0 else { return 0.0 }
        return Double(currentQuestionIndex) / Double(totalQuestions)
    }

    var allQuestionsAnswered: Bool {
        guard let challenge = currentChallenge else { return false }
        return selectedAnswers.count + timedOutQuestions.count >= challenge.questions.count
    }

    var totalTimeElapsed: TimeInterval {
        guard !questionStartTimes.isEmpty else { return 0 }
        let now = Date()
        return questionStartTimes.values.reduce(0.0) { total, startTime in
            total + now.timeIntervalSince(startTime)
        }
    }

    // MARK: - Initialization
    init(quizService: QuizServiceProtocol) {
        self.quizService = quizService
    }

    deinit {
        // Clean up timers
        stopAllTimers()
    }

    // MARK: - Public Methods

    func loadQuizHistory() async {
        isLoading = true
        errorMessage = nil

        do {
            quizHistory = try await quizService.getQuizHistory()
        } catch {
            handleError(error)
        }

        isLoading = false
    }

    func startQuiz(difficulty: QuizDifficulty, questionCount: Int) async {
        isLoading = true
        errorMessage = nil

        // Reset state
        resetQuizState()

        do {
            let challenge = try await quizService.generateChallenge(
                difficulty: difficulty,
                questionCount: questionCount
            )

            currentChallenge = challenge
            currentScreen = .active
            currentQuestionIndex = 0

            // Start timer for first question
            if let firstQuestion = challenge.questions.first {
                startQuestionTimer(questionId: firstQuestion.questionId)
            }

        } catch {
            handleError(error)
        }

        isLoading = false
    }

    func selectAnswer(questionId: String, optionId: String) {
        // Stop timer for this question
        stopQuestionTimer(questionId: questionId)

        // Record answer
        selectedAnswers[questionId] = optionId

        // Record completion time
        questionEndTimes[questionId] = Date()

        // Auto-advance to next question after brief delay
        Task {
            try? await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
            await advanceToNextQuestion()
        }
    }

    func advanceToNextQuestion() async {
        guard let challenge = currentChallenge else { return }

        // If we've answered all questions, we can submit
        if currentQuestionIndex >= challenge.questions.count - 1 {
            // Last question answered, ready to submit
            return
        }

        // Move to next question
        currentQuestionIndex += 1

        // Start timer for next question
        if currentQuestionIndex < challenge.questions.count {
            let nextQuestion = challenge.questions[currentQuestionIndex]
            startQuestionTimer(questionId: nextQuestion.questionId)
        }
    }

    func startQuestionTimer(questionId: String, timeLimit: Double = 15.0) {
        // Stop any existing timer for this question
        stopQuestionTimer(questionId: questionId)

        // Record start time
        questionStartTimes[questionId] = Date()
        questionTimeRemaining[questionId] = timeLimit

        // Create timer that updates every 0.1 seconds
        let timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] timer in
            Task { @MainActor [weak self] in
                guard let self = self else {
                    timer.invalidate()
                    return
                }

                guard let remaining = self.questionTimeRemaining[questionId] else {
                    timer.invalidate()
                    return
                }

                if remaining <= 0 {
                    // Timer expired
                    timer.invalidate()
                    self.questionTimers.removeValue(forKey: questionId)
                    self.handleTimerExpiration(questionId: questionId)
                } else {
                    // Update remaining time - reassign dictionary to trigger @Published
                    var updated = self.questionTimeRemaining
                    updated[questionId] = max(0, remaining - 0.1)
                    self.questionTimeRemaining = updated
                }
            }
        }

        questionTimers[questionId] = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    func stopQuestionTimer(questionId: String) {
        questionTimers[questionId]?.invalidate()
        questionTimers.removeValue(forKey: questionId)
    }

    func handleTimerExpiration(questionId: String) {
        // Mark question as timed out
        timedOutQuestions.insert(questionId)

        // Record completion time (used full time limit)
        questionEndTimes[questionId] = Date()

        // Auto-advance to next question after brief delay
        Task {
            try? await Task.sleep(nanoseconds: 1_500_000_000) // 1.5 seconds for "Time's up!" message
            await advanceToNextQuestion()
        }
    }

    func submitQuiz() async {
        guard let challenge = currentChallenge else { return }

        // Stop all timers
        stopAllTimers()

        isSubmitting = true
        errorMessage = nil

        // Calculate total time taken
        let totalTimeSeconds = calculateTotalTime()

        // Build answers array (including empty answers for timed out questions)
        var answers: [QuizAnswer] = []
        for question in challenge.questions {
            if let selectedOptionId = selectedAnswers[question.questionId] {
                answers.append(QuizAnswer(questionId: question.questionId, selected: selectedOptionId))
            } else if timedOutQuestions.contains(question.questionId) {
                // Timed out - submit with empty/invalid answer
                answers.append(QuizAnswer(questionId: question.questionId, selected: "timeout"))
            } else {
                // No answer selected (shouldn't happen if allQuestionsAnswered is true)
                answers.append(QuizAnswer(questionId: question.questionId, selected: "none"))
            }
        }

        do {
            let result = try await quizService.submitQuiz(
                challengeId: challenge.challengeId,
                answers: answers,
                timeTakenSeconds: totalTimeSeconds
            )

            quizResult = result
            currentScreen = .results

        } catch {
            handleError(error)
        }

        isSubmitting = false
    }

    func calculateTotalTime() -> Int {
        guard !questionStartTimes.isEmpty else { return 0 }

        var totalTime: TimeInterval = 0

        for (questionId, startTime) in questionStartTimes {
            if let endTime = questionEndTimes[questionId] {
                // Question was completed (answered or timed out)
                let timeTaken = endTime.timeIntervalSince(startTime)
                totalTime += timeTaken
            } else {
                // Question not yet completed (shouldn't happen when submitting)
                // Use current time as fallback
                let timeTaken = Date().timeIntervalSince(startTime)
                totalTime += timeTaken
            }
        }

        return Int(totalTime)
    }

    func getTimeRemaining(questionId: String) -> Double {
        return questionTimeRemaining[questionId] ?? 0.0
    }

    func resetQuizState() {
        stopAllTimers()
        currentChallenge = nil
        currentQuestionIndex = 0
        selectedAnswers.removeAll()
        questionStartTimes.removeAll()
        questionEndTimes.removeAll()
        questionTimeRemaining.removeAll()
        timedOutQuestions.removeAll()
        quizResult = nil
    }

    func returnToLobby() {
        resetQuizState()
        currentScreen = .lobby
        Task {
            await loadQuizHistory()
        }
    }

    // MARK: - Private Methods

    nonisolated private func stopAllTimers() {
        questionTimers.values.forEach { $0.invalidate() }
        questionTimers.removeAll()
    }

    private func handleError(_ error: Error) {
        if let quizError = error as? QuizError {
            switch quizError {
            case .dailyLimitReached:
                errorMessage = quizError.localizedDescription
            case .invalidChallenge:
                errorMessage = quizError.localizedDescription
                // Return to lobby if challenge is invalid
                returnToLobby()
            case .unauthorized:
                errorMessage = "Please sign in to take quizzes"
            default:
                errorMessage = quizError.localizedDescription
            }
        } else {
            errorMessage = "Failed to load quiz: \(error.localizedDescription)"
        }
    }
}
