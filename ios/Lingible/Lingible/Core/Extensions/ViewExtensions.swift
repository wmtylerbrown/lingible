import SwiftUI

// MARK: - Card Style Extension
extension View {
    func cardStyle() -> some View {
        self
            .background(Color(.systemBackground))
            .cornerRadius(16)
            .shadow(color: Color(.label).opacity(0.1), radius: 8, x: 0, y: 4)
    }
}
