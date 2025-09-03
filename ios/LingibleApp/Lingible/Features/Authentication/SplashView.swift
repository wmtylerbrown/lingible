import SwiftUI

struct SplashView: View {
    @State private var animatedTerms: [AnimatedTerm] = []
    @State private var showLogo = false
    @State private var showWordmark = false
    @State private var timer: Timer?

    // Slang words for background animation (from old app)
    private let slangTerms = [
        "slay", "periodt", "no cap", "fr fr", "bussin", "bet", "ngl", "tbh", "imo", "fyi",
        "lit", "fire", "vibe", "mood", "tea", "spill", "shade", "clapback", "flex", "drip",
        "sus", "simp", "stan", "ship", "otp", "bff", "bestie", "fam", "squad",
        "goals", "aesthetic", "vibes", "energy", "moment", "era", "phase", "journey", "glow up",
        "main character", "protagonist", "queen", "king", "icon", "legend", "hero", "savior"
    ]

    var body: some View {
        ZStack {
            // Background
            Color.lingibleBackground
                .ignoresSafeArea()

            // Animated slang words
            ForEach(animatedTerms) { term in
                Text(term.text)
                    .font(.system(size: term.fontSize, weight: .medium, design: .rounded))
                    .foregroundColor(term.color)
                    .opacity(term.opacity)
                    .position(term.position)
                    .scaleEffect(term.scale)
                    .rotationEffect(.degrees(term.rotation))
                    .animation(.easeInOut(duration: term.duration), value: term.opacity)
                    .animation(.easeInOut(duration: term.duration), value: term.scale)
                    .animation(.easeInOut(duration: term.duration), value: term.rotation)
            }

            // Logo and branding
            VStack(spacing: 16) {
                // Logo
                Image("LingibleLogo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 100, height: 100)
                    .opacity(showLogo ? 1 : 0)
                    .scaleEffect(showLogo ? 1 : 0.5)
                    .animation(.spring(response: 0.8, dampingFraction: 0.6), value: showLogo)

                // Wordmark
                Image("WordmarkMedium")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(height: 50)
                    .opacity(showWordmark ? 1 : 0)
                    .offset(y: showWordmark ? 0 : 20)
                    .animation(.spring(response: 0.8, dampingFraction: 0.8).delay(0.3), value: showWordmark)

                // Tagline
                Text("Bridge the gap between generations")
                    .font(.subheadline)
                    .foregroundColor(.lingibleSecondary)
                    .multilineTextAlignment(.center)
                    .opacity(showWordmark ? 1 : 0)
                    .animation(.easeIn(duration: 0.6).delay(0.6), value: showWordmark)
            }
        }
        .onAppear {
            startAnimations()
        }
        .onDisappear {
            stopAnimations()
        }
    }

    // MARK: - Animation Methods
    private func startAnimations() {
        // Show logo and wordmark
        withAnimation {
            showLogo = true
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            withAnimation {
                showWordmark = true
            }
        }

        // Start background term animations
        addNewTerm()
        addNewTerm()
        addNewTerm()

        timer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { _ in
            addNewTerm()
        }
    }

    private func stopAnimations() {
        timer?.invalidate()
        timer = nil
    }

    private func addNewTerm() {
        let term = slangTerms.randomElement() ?? "slay"
        let screenWidth = UIScreen.main.bounds.width
        let screenHeight = UIScreen.main.bounds.height

        let newAnimatedTerm = AnimatedTerm(
            id: UUID(),
            text: term,
            position: CGPoint(
                x: CGFloat.random(in: 50...(screenWidth - 50)),
                y: CGFloat.random(in: 100...(screenHeight - 200))
            ),
            fontSize: CGFloat.random(in: 12...20),
            color: [.lingiblePrimary, .lingibleSecondary, .orange, .purple, .pink].randomElement() ?? .lingiblePrimary,
            opacity: 0.0,
            scale: 0.8,
            rotation: Double.random(in: -15...15),
            duration: Double.random(in: 2.0...4.0)
        )

        animatedTerms.append(newAnimatedTerm)

        // Animate the term in
        withAnimation(.easeIn(duration: 0.5)) {
            if let index = animatedTerms.firstIndex(where: { $0.id == newAnimatedTerm.id }) {
                animatedTerms[index].opacity = 0.4
                animatedTerms[index].scale = 1.0
            }
        }

        // Animate the term out after a delay
        DispatchQueue.main.asyncAfter(deadline: .now() + newAnimatedTerm.duration) {
            withAnimation(.easeOut(duration: 0.5)) {
                if let index = animatedTerms.firstIndex(where: { $0.id == newAnimatedTerm.id }) {
                    animatedTerms[index].opacity = 0.0
                    animatedTerms[index].scale = 0.8
                }
            }

            // Remove the term after animation
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                animatedTerms.removeAll { $0.id == newAnimatedTerm.id }
            }
        }

        // Keep array size manageable
        if animatedTerms.count > 6 {
            animatedTerms.removeFirst()
        }
    }
}

// MARK: - Animated Term Model
struct AnimatedTerm: Identifiable {
    let id: UUID
    let text: String
    let position: CGPoint
    let fontSize: CGFloat
    let color: Color
    var opacity: Double
    var scale: Double
    let rotation: Double
    let duration: Double
}

#Preview {
    SplashView()
}
