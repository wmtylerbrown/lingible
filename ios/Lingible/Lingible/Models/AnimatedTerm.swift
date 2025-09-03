import SwiftUI

// MARK: - Supporting Types for Animated Terms
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
