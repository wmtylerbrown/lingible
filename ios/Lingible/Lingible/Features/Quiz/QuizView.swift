import SwiftUI

struct QuizView: View {
    @StateObject private var viewModel: QuizViewModel
    @EnvironmentObject var appCoordinator: AppCoordinator

    init(
        quizService: QuizServiceProtocol
    ) {
        self._viewModel = StateObject(wrappedValue: QuizViewModel(
            quizService: quizService
        ))
    }

    var body: some View {
        Group {
            switch viewModel.currentScreen {
            case .lobby:
                QuizLobbyView(viewModel: viewModel)
            case .active:
                NavigationView {
                    QuizActiveView(viewModel: viewModel)
                        .navigationTitle("Quiz")
                        .navigationBarTitleDisplayMode(.inline)
                        .navigationBarBackButtonHidden(true)
                }
            case .results:
                NavigationView {
                    QuizResultsView(viewModel: viewModel)
                }
            }
        }
        .alert("Quiz Error", isPresented: .constant(viewModel.errorMessage != nil)) {
            Button("OK") {
                viewModel.errorMessage = nil
            }
        } message: {
            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
            }
        }
        .onAppear {
            // Load quiz history on appear
            if viewModel.quizHistory == nil {
                Task {
                    await viewModel.loadQuizHistory()
                }
            }
        }
    }
}
