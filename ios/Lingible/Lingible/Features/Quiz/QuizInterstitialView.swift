import SwiftUI

// MARK: - Quiz Interstitial Loading View
struct QuizInterstitialView: View {
    @State private var animatedTerms: [AnimatedTerm] = []
    @State private var currentMessage: String = ""
    @State private var timer: Timer?
    @State private var pulseScale: CGFloat = 1.0
    @State private var glowIntensity: Double = 0.3
    @State private var gradientOffset: Double = 0.0
    @State private var animationTimer: Timer?

    // Slang words for background animation (same as SplashView)
    private let slangTerms = [
        "slay", "periodt", "no cap", "fr fr", "bussin", "bet", "ngl", "tbh", "imo", "fyi",
        "lit", "fire", "vibe", "mood", "tea", "spill", "shade", "clapback", "flex", "drip",
        "sus", "simp", "stan", "ship", "otp", "bff", "bestie", "fam", "squad",
        "goals", "aesthetic", "vibes", "energy", "moment", "era", "phase", "journey", "glow up",
        "main character", "protagonist", "queen", "king", "icon", "legend", "hero", "savior",
        "slaps", "banger", "bop", "jam", "tune", "track", "song", "melody", "rhythm", "beat",
        "groove", "flow", "swag", "style", "fashion", "look", "fit", "outfit", "ensemble",
        "snatched", "serving", "giving", "delivering", "executing", "performing", "acting", "doing"
    ]

    // On-brand status messages (rotating)
    private let statusMessages = [
        "Slaying the next question...",
        "No cap, this one's fire...",
        "Getting that Gen Z knowledge...",
        "Loading some bussin content...",
        "Almost ready to flex...",
        "This question's about to hit...",
        "Keep the vibes going...",
        "Next question incoming...",
        "That question was valid...",
        "Ready to slay again..."
    ]

    var body: some View {
        ZStack {
            // Background
            Color.lingibleBackground
                .ignoresSafeArea()

            // Subtle background pattern for better term visibility
            ForEach(0..<6, id: \.self) { index in
                Circle()
                    .fill(Color.lingiblePrimary.opacity(0.03))
                    .frame(width: CGFloat.random(in: 100...300))
                    .position(
                        x: CGFloat.random(in: 0...UIScreen.main.bounds.width),
                        y: CGFloat.random(in: 0...UIScreen.main.bounds.height)
                    )
                    .blur(radius: 20)
                    .zIndex(0)
            }

            // Animated slang words (background layer)
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
                    .zIndex(1)
            }

            // Centered status message (foreground)
            VStack(spacing: 16) {
                Text(currentMessage)
                    .font(.headline)
                    .fontWeight(.medium)
                    .foregroundStyle(
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color.lingiblePrimary,
                                Color.lingibleSecondary,
                                Color.lingiblePrimary.opacity(0.8)
                            ]),
                            startPoint: UnitPoint(
                                x: 0.5 + gradientOffset,
                                y: 0
                            ),
                            endPoint: UnitPoint(
                                x: 0.5 - gradientOffset,
                                y: 1
                            )
                        )
                    )
                    .multilineTextAlignment(.center)
                    .scaleEffect(pulseScale)
                    .shadow(color: Color.lingiblePrimary.opacity(glowIntensity), radius: 8, x: 0, y: 0)
                    .transition(.opacity.combined(with: .scale))
            }
            .padding(20)
            .background(.ultraThinMaterial)
            .cornerRadius(16)
            .padding(.horizontal, 40)
            .zIndex(10)
        }
        .onAppear {
            selectRandomMessage()
            startAnimations()
        }
        .onDisappear {
            stopAnimations()
        }
    }

    // MARK: - Message Selection
    private func selectRandomMessage() {
        // Select a random message, ensuring we don't repeat the last one
        var selectedMessage = statusMessages.randomElement() ?? "Getting next question..."
        var attempts = 0

        // Try to avoid immediate repetition (simple check)
        while selectedMessage == currentMessage && attempts < 5 && !currentMessage.isEmpty {
            selectedMessage = statusMessages.randomElement() ?? "Getting next question..."
            attempts += 1
        }

        withAnimation(.easeIn(duration: 0.3)) {
            currentMessage = selectedMessage
        }
    }

    // MARK: - Animation Methods
    private func startAnimations() {
        // Start with a few terms immediately
        addNewTerm()
        addNewTerm()
        addNewTerm()

        // Continue adding terms every 1.2 seconds
        timer = Timer.scheduledTimer(withTimeInterval: 1.2, repeats: true) { _ in
            addNewTerm()
        }

        // Start pulse and glow animations
        startPulseAnimation()
        startGradientAnimation()
    }

    private func stopAnimations() {
        timer?.invalidate()
        timer = nil
        animationTimer?.invalidate()
        animationTimer = nil
    }

    private func startPulseAnimation() {
        // Gentle pulse animation: 1.0 → 1.015 over 2.5 seconds (very subtle)
        withAnimation(
            .easeInOut(duration: 2.5)
            .repeatForever(autoreverses: true)
        ) {
            pulseScale = 1.015
        }

        // Glow intensity animation: 0.3 → 0.5 → 0.3 over 1.5 seconds (subtle)
        withAnimation(
            .easeInOut(duration: 1.5)
            .repeatForever(autoreverses: true)
        ) {
            glowIntensity = 0.5
        }
    }

    private func startGradientAnimation() {
        // Gradient shift animation: slow color transition
        animationTimer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { _ in
            withAnimation(.linear(duration: 0.05)) {
                gradientOffset = (gradientOffset + 0.02).truncatingRemainder(dividingBy: 1.0)
            }
        }
    }

    private func addNewTerm() {
        let term = slangTerms.randomElement() ?? "slay"
        let screenWidth = UIScreen.main.bounds.width
        let screenHeight = UIScreen.main.bounds.height

        // Define safe zones to avoid center (where message is)
        let statusBarHeight: CGFloat = 50
        let centerZoneHeight: CGFloat = 200
        let centerZoneY: CGFloat = (screenHeight - centerZoneHeight) / 2
        let centerZoneWidth: CGFloat = 180
        let centerZoneX: CGFloat = (screenWidth - centerZoneWidth) / 2

        // Generate position avoiding the center zone
        var position: CGPoint
        var attempts = 0
        let maxAttempts = 15

        repeat {
            let zone = Int.random(in: 0...3)
            let x: CGFloat
            let y: CGFloat

            switch zone {
            case 0: // Top left area
                x = CGFloat.random(in: 20...(centerZoneX - 10))
                y = CGFloat.random(in: (statusBarHeight + 20)...(centerZoneY - 10))
            case 1: // Top right area
                x = CGFloat.random(in: (centerZoneX + centerZoneWidth + 10)...(screenWidth - 20))
                y = CGFloat.random(in: (statusBarHeight + 20)...(centerZoneY - 10))
            case 2: // Bottom left area
                x = CGFloat.random(in: 20...(centerZoneX - 10))
                y = CGFloat.random(in: (centerZoneY + centerZoneHeight + 10)...(screenHeight - 80))
            case 3: // Bottom right area
                x = CGFloat.random(in: (centerZoneX + centerZoneWidth + 10)...(screenWidth - 20))
                y = CGFloat.random(in: (centerZoneY + centerZoneHeight + 10)...(screenHeight - 80))
            default:
                x = CGFloat.random(in: 20...(screenWidth - 20))
                y = CGFloat.random(in: (statusBarHeight + 20)...(screenHeight - 80))
            }

            position = CGPoint(x: x, y: y)
            attempts += 1

            let isInCenterZone = x >= centerZoneX && x <= (centerZoneX + centerZoneWidth) &&
                                y >= centerZoneY && y <= (centerZoneY + centerZoneHeight)

            if !isInCenterZone || attempts >= maxAttempts {
                break
            }
        } while attempts < maxAttempts

        let newAnimatedTerm = AnimatedTerm(
            id: UUID(),
            text: term,
            position: position,
            fontSize: CGFloat.random(in: 16...28),
            color: [.lingiblePrimary, .lingibleSecondary, .orange, .purple, .pink].randomElement() ?? .lingiblePrimary,
            opacity: 0.0,
            scale: 0.8,
            rotation: Double.random(in: -20...20),
            duration: Double.random(in: 2.5...4.5)
        )

        animatedTerms.append(newAnimatedTerm)

        // Animate the term in
        withAnimation(.easeIn(duration: 0.6)) {
            if let index = animatedTerms.firstIndex(where: { $0.id == newAnimatedTerm.id }) {
                animatedTerms[index].opacity = 0.9
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
        if animatedTerms.count > 12 {
            animatedTerms.removeFirst()
        }
    }
}
