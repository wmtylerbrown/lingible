import SwiftUI
import LingibleAPI

struct UsageProgressView: View {
    let currentUsage: Int
    let dailyLimit: Int

    private var progressPercentage: Double {
        guard dailyLimit > 0 else { return 0 }
        return min(Double(currentUsage) / Double(dailyLimit), 1.0)
    }

    private var isNearLimit: Bool {
        progressPercentage >= 0.8
    }

    private var isAtLimit: Bool {
        currentUsage >= dailyLimit
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Usage counter
            HStack {
                Text("Daily Translations")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Spacer()
                Text("\(currentUsage)/\(dailyLimit)")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(isAtLimit ? .red : .primary)
            }

            // Progress bar
            ProgressView(value: progressPercentage)
                .progressViewStyle(LinearProgressViewStyle(tint: progressColor))
                .scaleEffect(x: 1, y: 1.5, anchor: .center)

            // Status message
            if isAtLimit {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.orange)
                        .font(.caption)
                    Text("Daily limit reached. Upgrade for 100 daily translations!")
                        .font(.caption)
                        .foregroundColor(.orange)
                        .fontWeight(.medium)
                }
            } else if isNearLimit {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.circle.fill")
                        .foregroundColor(.orange)
                        .font(.caption)
                    Text("Almost at daily limit. Consider upgrading!")
                        .font(.caption)
                        .foregroundColor(.orange)
                        .fontWeight(.medium)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(.systemGray6))
        .cornerRadius(12)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Daily translations: \(currentUsage) of \(dailyLimit)")
        .accessibilityValue(isAtLimit ? "Daily limit reached" : "\(dailyLimit - currentUsage) translations remaining")
    }

    private var progressColor: Color {
        if isAtLimit {
            return .red
        } else if isNearLimit {
            return .orange
        } else {
            return .lingiblePrimary
        }
    }
}

#Preview("Free User - Near Limit") {
    UsageProgressView(currentUsage: 8, dailyLimit: 10)
        .padding()
}

#Preview("Free User - At Limit") {
    UsageProgressView(currentUsage: 10, dailyLimit: 10)
        .padding()
}

#Preview("Premium User") {
    UsageProgressView(currentUsage: 25, dailyLimit: 100)
        .padding()
}
