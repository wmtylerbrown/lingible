import SwiftUI

// MARK: - Custom View Modifiers

/// Scale animation on button press
struct ScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

/// Fade in animation
struct FadeInModifier: ViewModifier {
    let delay: Double
    @State private var opacity: Double = 0

    func body(content: Content) -> some View {
        content
            .opacity(opacity)
            .onAppear {
                withAnimation(.easeIn(duration: 0.6).delay(delay)) {
                    opacity = 1
                }
            }
    }
}

/// Card style modifier
struct CardStyle: ViewModifier {
    let backgroundColor: Color
    let shadowRadius: CGFloat
    let cornerRadius: CGFloat

    init(
        backgroundColor: Color = .lingibleLightBackground,
        shadowRadius: CGFloat = 8,
        cornerRadius: CGFloat = 16
    ) {
        self.backgroundColor = backgroundColor
        self.shadowRadius = shadowRadius
        self.cornerRadius = cornerRadius
    }

    func body(content: Content) -> some View {
        content
            .background(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .fill(backgroundColor)
                    .shadow(
                        color: .black.opacity(0.1),
                        radius: shadowRadius,
                        x: 0,
                        y: 4
                    )
            )
    }
}

// MARK: - View Extensions
extension View {
    /// Apply scale animation to buttons
    func scaleAnimation() -> some View {
        self.buttonStyle(ScaleButtonStyle())
    }

    /// Apply fade in animation
    func fadeInAnimation(delay: Double = 0) -> some View {
        self.modifier(FadeInModifier(delay: delay))
    }

    /// Apply card styling
    func cardStyle(
        backgroundColor: Color = .lingibleLightBackground,
        shadowRadius: CGFloat = 8,
        cornerRadius: CGFloat = 16
    ) -> some View {
        self.modifier(CardStyle(
            backgroundColor: backgroundColor,
            shadowRadius: shadowRadius,
            cornerRadius: cornerRadius
        ))
    }

    /// Hide keyboard
    func hideKeyboard() {
        UIApplication.shared.sendAction(
            #selector(UIResponder.resignFirstResponder),
            to: nil,
            from: nil,
            for: nil
        )
    }
}
