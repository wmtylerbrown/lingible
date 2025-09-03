import SwiftUI

struct TranslationView: View {
    @StateObject private var viewModel = TranslationViewModel()
    @State private var inputText = ""
    @State private var showInputCard = true

    var body: some View {
        NavigationView {
            ZStack {
                Color.lingibleBackground
                    .ignoresSafeArea()
                    .onTapGesture {
                        hideKeyboard()
                    }

                VStack(spacing: 0) {
                    // Header
                    headerView

                    // Content
                    if showInputCard {
                        inputCardView
                            .padding(.horizontal, 20)
                            .padding(.top, 20)
                    }

                    // Results
                    if !viewModel.translationHistory.isEmpty {
                        translationHistoryView
                    }

                    Spacer()
                }
            }
            .navigationBarHidden(true)
        }
    }

    // MARK: - Header View
    private var headerView: some View {
        HStack {
            // Logo + Wordmark
            HStack(spacing: 8) {
                Image("LingibleLogo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 40, height: 40)

                Image("WordmarkMedium")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(height: 30)
            }

            Spacer()

            // New translation button
            Button(action: {
                inputText = ""
                withAnimation(.spring()) {
                    showInputCard = true
                }
            }) {
                Image(systemName: "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(.lingiblePrimary)
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 8)
        .padding(.bottom, 16)
    }

    // MARK: - Input Card View
    private var inputCardView: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            HStack {
                Image(systemName: "text.bubble")
                    .font(.title3)
                    .foregroundColor(.lingiblePrimary)

                Text("Enter text to translate")
                    .font(.headline)
                    .foregroundColor(.primary)

                Spacer()
            }

            // Input field
            TextEditor(text: $inputText)
                .frame(minHeight: 80)
                .padding(12)
                .background(Color.white)
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.lingiblePrimary.opacity(0.2), lineWidth: 1)
                )

            // Character count
            HStack {
                Spacer()
                Text("\(inputText.count)/500")
                    .font(.caption)
                    .foregroundColor(.lingibleSecondary)
            }

            // Translate button
            Button(action: translate) {
                HStack {
                    if viewModel.isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                            .foregroundColor(.white)
                        Text("Translating...")
                    } else {
                        Text("Translate")
                    }
                }
                .font(.headline)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(
                    inputText.isEmpty ? Color.gray : Color.lingiblePrimary
                )
                .cornerRadius(12)
            }
            .disabled(inputText.isEmpty || viewModel.isLoading)
            .scaleAnimation()
        }
        .padding(20)
        .cardStyle()
    }

    // MARK: - Translation History View
    private var translationHistoryView: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                ForEach(viewModel.translationHistory, id: \.id) { translation in
                    TranslationResultCard(translation: translation)
                        .padding(.horizontal, 20)
                }
            }
            .padding(.top, 20)
        }
    }

    // MARK: - Actions
    private func translate() {
        guard !inputText.isEmpty else { return }

        Task {
            await viewModel.translate(text: inputText)

            // Hide input card after successful translation
            if !viewModel.translationHistory.isEmpty {
                withAnimation(.spring()) {
                    showInputCard = false
                }
            }
        }
    }
}

// MARK: - Translation Result Card
struct TranslationResultCard: View {
    let translation: TranslationHistoryItem

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Header
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .font(.title2)
                    .foregroundColor(.green)

                Text("Translation")
                    .font(.headline)
                    .fontWeight(.semibold)

                Spacer()

                Text(translation.createdAt, style: .time)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            // Original text
            VStack(alignment: .leading, spacing: 8) {
                Text("Gen Z:")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.originalText)
                    .font(.body)
                    .padding(12)
                    .background(Color.lingibleSecondary.opacity(0.1))
                    .cornerRadius(8)
            }

            // Translated text
            VStack(alignment: .leading, spacing: 8) {
                Text("Translation:")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(translation.translatedText)
                    .font(.body)
                    .padding(12)
                    .background(Color.lingiblePrimary.opacity(0.1))
                    .cornerRadius(8)
            }
        }
        .padding(20)
        .cardStyle()
    }
}

#Preview {
    TranslationView()
}
