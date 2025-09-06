import SwiftUI
import LingibleAPI

// MARK: - Enhanced Header with Upgrade Button
struct EnhancedHeader: View {
    let title: String?
    let actionButton: HeaderActionButton?
    let userTier: UsageResponse.Tier?
    let onUpgradeTap: (() -> Void)?
    
    @State private var isUpgradeButtonPressed = false
    
    init(
        title: String? = nil,
        actionButton: HeaderActionButton? = nil,
        userTier: UsageResponse.Tier? = nil,
        onUpgradeTap: (() -> Void)? = nil
    ) {
        self.title = title
        self.actionButton = actionButton
        self.userTier = userTier
        self.onUpgradeTap = onUpgradeTap
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Main header content
            HStack {
                // Logo + Wordmark
                HStack(spacing: 2) {
                    Image("LingibleLogo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 60, height: 60)
                    
                    Image("WordmarkMedium")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(height: 35)
                }
                
                Spacer()
                
                // Right side buttons
                HStack(spacing: 12) {
                    // Upgrade button (only for free users)
                    if userTier == .free {
                        upgradeButton
                    }
                    
                    // Action button (if provided)
                    if let actionButton = actionButton {
                        Button(action: actionButton.action) {
                            Image(systemName: actionButton.iconName)
                                .font(.title2)
                                .foregroundColor(.lingiblePrimary)
                        }
                    }
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 8)
            .padding(.bottom, 16)
        }
    }
    
    // MARK: - Upgrade Button
    private var upgradeButton: some View {
        Button(action: {
            onUpgradeTap?()
        }) {
            HStack(spacing: 6) {
                Image(systemName: "star.fill")
                    .font(.caption)
                    .foregroundColor(.white)
                
                Text("Upgrade")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color.lingiblePrimary,
                        Color.lingiblePrimary.opacity(0.8)
                    ]),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .cornerRadius(16)
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color(.systemBackground).opacity(0.3),
                                Color.clear
                            ]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 1
                    )
            )
            .shadow(
                color: Color.lingiblePrimary.opacity(0.3),
                radius: isUpgradeButtonPressed ? 2 : 4,
                x: 0,
                y: isUpgradeButtonPressed ? 1 : 2
            )
            .scaleEffect(isUpgradeButtonPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: isUpgradeButtonPressed)
        }
        .onLongPressGesture(minimumDuration: 0, maximumDistance: .infinity, pressing: { pressing in
            isUpgradeButtonPressed = pressing
        }, perform: {})
        .accessibilityLabel("Upgrade to Premium")
        .accessibilityHint("Tap to upgrade to premium features")
    }
}

// MARK: - Convenience Initializers
extension EnhancedHeader {
    /// Creates a header with just the logo and wordmark
    static func logoOnly(userTier: UsageResponse.Tier? = nil, onUpgradeTap: (() -> Void)? = nil) -> EnhancedHeader {
        EnhancedHeader(userTier: userTier, onUpgradeTap: onUpgradeTap)
    }
    
    /// Creates a header with a refresh button
    static func withRefresh(
        isLoading: Bool,
        userTier: UsageResponse.Tier? = nil,
        onRefresh: @escaping () -> Void,
        onUpgradeTap: (() -> Void)? = nil
    ) -> EnhancedHeader {
        EnhancedHeader(
            actionButton: HeaderActionButton(
                iconName: isLoading ? "arrow.clockwise" : "arrow.clockwise",
                action: onRefresh
            ),
            userTier: userTier,
            onUpgradeTap: onUpgradeTap
        )
    }
    
    /// Creates a header with a new/plus button
    static func withNewButton(
        userTier: UsageResponse.Tier? = nil,
        onNew: @escaping () -> Void,
        onUpgradeTap: (() -> Void)? = nil
    ) -> EnhancedHeader {
        EnhancedHeader(
            actionButton: HeaderActionButton(
                iconName: "plus.circle.fill",
                action: onNew
            ),
            userTier: userTier,
            onUpgradeTap: onUpgradeTap
        )
    }
    
    /// Creates a header with a custom action button
    static func withCustomButton(
        iconName: String,
        userTier: UsageResponse.Tier? = nil,
        onAction: @escaping () -> Void,
        onUpgradeTap: (() -> Void)? = nil
    ) -> EnhancedHeader {
        EnhancedHeader(
            actionButton: HeaderActionButton(
                iconName: iconName,
                action: onAction
            ),
            userTier: userTier,
            onUpgradeTap: onUpgradeTap
        )
    }
}

// MARK: - Preview
#Preview {
    VStack(spacing: 20) {
        // Free user with upgrade button
        EnhancedHeader.logoOnly(
            userTier: .free,
            onUpgradeTap: { print("Upgrade tapped") }
        )
        
        // Premium user (no upgrade button)
        EnhancedHeader.logoOnly(
            userTier: .premium,
            onUpgradeTap: { print("Upgrade tapped") }
        )
        
        // With refresh button
        EnhancedHeader.withRefresh(
            isLoading: false,
            userTier: .free,
            onRefresh: { print("Refresh tapped") },
            onUpgradeTap: { print("Upgrade tapped") }
        )
        
        // With new button
        EnhancedHeader.withNewButton(
            userTier: .free,
            onNew: { print("New tapped") },
            onUpgradeTap: { print("Upgrade tapped") }
        )
    }
    .background(Color.lingibleBackground)
}
