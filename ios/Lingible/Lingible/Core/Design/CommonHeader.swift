import SwiftUI

// MARK: - Common Header Component
struct CommonHeader: View {
    let title: String?
    let actionButton: HeaderActionButton?

    init(title: String? = nil, actionButton: HeaderActionButton? = nil) {
        self.title = title
        self.actionButton = actionButton
    }

    var body: some View {
        HStack {
            // Logo + Wordmark
            HStack(spacing: 8) {
                Image("LingibleLogo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 50, height: 50)

                Image("WordmarkMedium")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(height: 35)
            }

            Spacer()

            // Action button (if provided)
            if let actionButton = actionButton {
                Button(action: actionButton.action) {
                    Image(systemName: actionButton.iconName)
                        .font(.title2)
                        .foregroundColor(.lingiblePrimary)
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 8)
        .padding(.bottom, 16)
    }
}

// MARK: - Header Action Button
struct HeaderActionButton {
    let iconName: String
    let action: () -> Void

    init(iconName: String, action: @escaping () -> Void) {
        self.iconName = iconName
        self.action = action
    }
}

// MARK: - Convenience Initializers
extension CommonHeader {
    /// Creates a header with just the logo and wordmark
    static func logoOnly() -> CommonHeader {
        CommonHeader()
    }

    /// Creates a header with a refresh button
    static func withRefresh(isLoading: Bool, action: @escaping () -> Void) -> CommonHeader {
        CommonHeader(
            actionButton: HeaderActionButton(
                iconName: isLoading ? "arrow.clockwise" : "arrow.clockwise",
                action: action
            )
        )
    }

    /// Creates a header with a new/plus button
    static func withNewButton(action: @escaping () -> Void) -> CommonHeader {
        CommonHeader(
            actionButton: HeaderActionButton(
                iconName: "plus.circle.fill",
                action: action
            )
        )
    }

    /// Creates a header with a custom action button
    static func withCustomButton(iconName: String, action: @escaping () -> Void) -> CommonHeader {
        CommonHeader(
            actionButton: HeaderActionButton(
                iconName: iconName,
                action: action
            )
        )
    }
}

// MARK: - Preview
#Preview {
    VStack(spacing: 20) {
        // Logo only
        CommonHeader.logoOnly()

        // With refresh button
        CommonHeader.withRefresh(isLoading: false) {
            print("Refresh tapped")
        }

        // With new button
        CommonHeader.withNewButton {
            print("New tapped")
        }

        // With custom button
        CommonHeader.withCustomButton(iconName: "gear") {
            print("Settings tapped")
        }
    }
    .background(Color.lingibleBackground)
}
