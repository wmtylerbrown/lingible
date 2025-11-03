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
    @Published var currentSessionId: String?
    @Published var currentQuestion: QuizQuestion?
    @Published var sessionProgress: QuizSessionProgress?
    @Published var lastAnswerResponse: QuizAnswerResponse?
    @Published var questionStartTimes: [String: Date] = [:]
    @Published var questionTimeRemaining: [String: Double] = [:] // questionId -> remaining seconds
    @Published var timedOutQuestions: Set<String> = []
    @Published var isSubmitting: Bool = false
    @Published var quizResult: QuizResult?
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var currentScreen: QuizScreen = .lobby
    @Published var showingInterstitial: Bool = false

    // MARK: - Private Properties
    private let quizService: QuizServiceProtocol
    nonisolated(unsafe) private var questionTimers: [String: Timer] = [:]
    private let defaultQuestionTimeLimit: Double = 15.0 // seconds per question

    // MARK: - Computed Properties
    var questionsAnswered: Int {
        sessionProgress?.questionsAnswered ?? 0
    }

    var totalScore: Float {
        sessionProgress?.totalScore ?? 0.0
    }

    var accuracy: Float {
        sessionProgress?.accuracy ?? 0.0
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

    func startQuiz() async {
        isLoading = true
        errorMessage = nil

        // Reset state
        resetQuizState()

        do {
            // Get first question (default difficulty: beginner)
            let questionResponse = try await quizService.getNextQuestion(difficulty: nil)

            // Store session ID and first question
            currentSessionId = questionResponse.sessionId
            currentQuestion = questionResponse.question
            currentScreen = .active

            // Start timer for first question
            startQuestionTimer(questionId: questionResponse.question.questionId)

        } catch {
            handleError(error)
        }

        isLoading = false
    }

    func selectAnswer(questionId: String, optionId: String) async {
        guard let sessionId = currentSessionId else { return }

        // Stop timer for this question
        stopQuestionTimer(questionId: questionId)

        // Calculate time taken
        let timeTaken = calculateTimeTaken(questionId: questionId)

        // Create answer request
        let answerRequest = QuizAnswerRequest(
            sessionId: sessionId,
            questionId: questionId,
            selectedOption: optionId,
            timeTakenSeconds: Float(timeTaken)
        )

        isSubmitting = true
        errorMessage = nil

        do {
            // Submit answer immediately and get feedback
            let response = try await quizService.submitAnswer(request: answerRequest)

            // Store response for UI feedback
            lastAnswerResponse = response
            sessionProgress = response.runningStats

            // Show feedback briefly, then show interstitial
            try? await Task.sleep(nanoseconds: 1_500_000_000) // 1.5 seconds for feedback

            // Clear feedback and show interstitial
            lastAnswerResponse = nil
            showingInterstitial = true

            // Show interstitial for 2.5 seconds
            try? await Task.sleep(nanoseconds: 2_500_000_000) // 2.5 seconds for interstitial

            // Hide interstitial and fetch next question
            showingInterstitial = false
            await getNextQuestion()

        } catch {
            handleError(error)
            isSubmitting = false
        }

        isSubmitting = false
    }

    func getNextQuestion() async {
        guard currentSessionId != nil else { return }

        isLoading = true
        errorMessage = nil

        do {
            // Get next question (uses existing session)
            let questionResponse = try await quizService.getNextQuestion(difficulty: nil)

            // Update session ID if it changed (shouldn't happen, but be safe)
            if currentSessionId != questionResponse.sessionId {
                currentSessionId = questionResponse.sessionId
            }

            // Update current question
            currentQuestion = questionResponse.question

            // Start timer for new question
            startQuestionTimer(questionId: questionResponse.question.questionId)

        } catch {
            handleError(error)
        }

        isLoading = false
    }

    func calculateTimeTaken(questionId: String) -> Double {
        guard let startTime = questionStartTimes[questionId] else {
            return defaultQuestionTimeLimit
        }
        let timeTaken = Date().timeIntervalSince(startTime)
        return min(timeTaken, defaultQuestionTimeLimit)
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
                    Task {
                        await self.handleTimerExpiration(questionId: questionId)
                    }
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

    func handleTimerExpiration(questionId: String) async {
        guard let sessionId = currentSessionId else { return }

        // Mark question as timed out
        timedOutQuestions.insert(questionId)

        // Submit empty/invalid answer for timed out question
        let answerRequest = QuizAnswerRequest(
            sessionId: sessionId,
            questionId: questionId,
            selectedOption: "", // Empty selection for timeout
            timeTakenSeconds: Float(defaultQuestionTimeLimit)
        )

        isSubmitting = true
        errorMessage = nil

        do {
            // Submit timeout answer
            let response = try await quizService.submitAnswer(request: answerRequest)

            // Update progress
            sessionProgress = response.runningStats

            // Show interstitial for timed out questions too
            showingInterstitial = true

            // Show interstitial for 2.5 seconds
            try? await Task.sleep(nanoseconds: 2_500_000_000) // 2.5 seconds for interstitial

            // Hide interstitial and fetch next question
            showingInterstitial = false
            await getNextQuestion()

        } catch {
            handleError(error)
        }

        isSubmitting = false
    }

    func endQuiz() async {
        guard let sessionId = currentSessionId else { return }

        // Stop all timers
        stopAllTimers()

        isSubmitting = true
        errorMessage = nil

        do {
            // End session and get final results
            let result = try await quizService.endSession(sessionId: sessionId)

            quizResult = result
            currentScreen = .results

            // Refresh history to show updated stats
            await loadQuizHistory()

        } catch {
            handleError(error)
        }

        isSubmitting = false
    }

    func getTimeRemaining(questionId: String) -> Double {
        return questionTimeRemaining[questionId] ?? 0.0
    }

    func resetQuizState() {
        stopAllTimers()
        currentSessionId = nil
        currentQuestion = nil
        sessionProgress = nil
        lastAnswerResponse = nil
        questionStartTimes.removeAll()
        questionTimeRemaining.removeAll()
        timedOutQuestions.removeAll()
        quizResult = nil
        showingInterstitial = false
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
                // Return to lobby if daily limit reached
                returnToLobby()
            case .unauthorized:
                errorMessage = "Please sign in to take quizzes"
                returnToLobby()
            case .networkError(let underlyingError):
                // Provide more specific network error messages
                let nsError = underlyingError as NSError
                if nsError.domain == NSURLErrorDomain {
                    switch nsError.code {
                    case NSURLErrorNotConnectedToInternet:
                        errorMessage = "No internet connection. Please check your network and try again."
                    case NSURLErrorTimedOut:
                        errorMessage = "Request timed out. Please try again."
                    default:
                        errorMessage = "Network error: \(underlyingError.localizedDescription)"
                    }
                } else {
                    errorMessage = "Network error: \(underlyingError.localizedDescription)"
                }
            default:
                errorMessage = quizError.localizedDescription
            }
        } else {
            // For any other error, provide a user-friendly message
            errorMessage = "Failed to load quiz: \(error.localizedDescription)"
        }
    }
}
