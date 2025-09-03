import SwiftUI

// MARK: - Card Style Extension
extension View {
    func cardStyle() -> some View {
        self
            .background(Color.white)
            .cornerRadius(16)
            .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 4)
    }
}
