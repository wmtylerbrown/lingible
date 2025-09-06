import SwiftUI
import LingibleAPI

// MARK: - Trending Term Card
struct TrendingTermCard: View {
    let term: TrendingTermResponse
    let userTier: UserTier
    @State private var isExpanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header with term and category
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(term.term ?? "Unknown Term")
                        .font(.headline)
                        .fontWeight(.bold)
                        .foregroundColor(.primary)

                    HStack(spacing: 8) {
                        Image(systemName: term.categoryIcon)
                            .foregroundColor(.lingiblePrimary)
                            .font(.caption)

                        Text(term.categoryDisplayName)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                // Popularity score
                VStack(alignment: .trailing, spacing: 2) {
                    Text("\(term.popularityPercentage)%")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(.lingiblePrimary)

                    Text("trending")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }

            // Definition
            Text(term.definition ?? "No definition available")
                .font(.body)
                .foregroundColor(.primary)
                .lineLimit(isExpanded ? nil : 3)

            // Premium content indicator
            if term.hasPremiumContent && userTier == .free {
                HStack {
                    Image(systemName: "crown.fill")
                        .foregroundColor(.orange)
                        .font(.caption)

                    Text("Premium content available")
                        .font(.caption)
                        .foregroundColor(.orange)
                        .fontWeight(.medium)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.orange.opacity(0.1))
                .cornerRadius(8)
            }

            // Expanded content for premium users
            if isExpanded && userTier == .premium {
                VStack(alignment: .leading, spacing: 8) {
                    // Example usage
                    if let exampleUsage = term.exampleUsage, !exampleUsage.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Example")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)

                            Text("\"\(exampleUsage)\"")
                                .font(.body)
                                .italic()
                                .foregroundColor(.primary)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(Color.gray.opacity(0.1))
                                .cornerRadius(8)
                        }
                    }

                    // Origin
                    if let origin = term.origin, !origin.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Origin")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)

                            Text(origin)
                                .font(.body)
                                .foregroundColor(.primary)
                        }
                    }

                    // Related terms
                    if let relatedTerms = term.relatedTerms, !relatedTerms.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Related Terms")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)

                            LazyVGrid(columns: [
                                GridItem(.adaptive(minimum: 80))
                            ], spacing: 8) {
                                ForEach(relatedTerms, id: \.self) { relatedTerm in
                                    Text(relatedTerm)
                                        .font(.caption)
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 4)
                                        .background(Color.lingiblePrimary.opacity(0.1))
                                        .foregroundColor(.lingiblePrimary)
                                        .cornerRadius(12)
                                }
                            }
                        }
                    }

                    // Stats for premium users
                    HStack(spacing: 16) {
                        if let searchCount = term.searchCount {
                            StatView(
                                icon: "magnifyingglass",
                                value: "\(searchCount)",
                                label: "searches"
                            )
                        }

                        if let translationCount = term.translationCount {
                            StatView(
                                icon: "arrow.left.arrow.right",
                                value: "\(translationCount)",
                                label: "translations"
                            )
                        }

                        StatView(
                            icon: "clock",
                            value: term.formattedFirstSeen,
                            label: "first seen"
                        )
                    }
                }
                .padding(.top, 8)
            }

            // Expand/collapse button
            if userTier == .premium && (term.hasPremiumContent || term.searchCount != nil || term.translationCount != nil) {
                Button(action: {
                    withAnimation(.easeInOut(duration: 0.3)) {
                        isExpanded.toggle()
                    }
                }) {
                    HStack {
                        Text(isExpanded ? "Show Less" : "Show More")
                            .font(.caption)
                            .fontWeight(.medium)

                        Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                            .font(.caption)
                    }
                    .foregroundColor(.lingiblePrimary)
                }
            }
        }
        .padding(16)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color(.label).opacity(0.05), radius: 2, x: 0, y: 1)
    }
}

// MARK: - Stat View
struct StatView: View {
    let icon: String
    let value: String
    let label: String

    var body: some View {
        VStack(spacing: 2) {
            Image(systemName: icon)
                .foregroundColor(.lingiblePrimary)
                .font(.caption)

            Text(value)
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundColor(.primary)

            Text(label)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
    }
}

// MARK: - Preview
#Preview {
    VStack(spacing: 16) {
        TrendingTermCard(
            term: TrendingTermResponse(
                term: "no cap",
                definition: "No lie, for real, I'm telling the truth",
                category: .slang,
                popularityScore: 85.5,
                searchCount: 1250,
                translationCount: 890,
                firstSeen: Date().addingTimeInterval(-86400 * 7), // 7 days ago
                lastUpdated: Date(),
                isActive: true,
                exampleUsage: "That movie was fire, no cap!",
                origin: "Hip hop culture",
                relatedTerms: ["fr", "for real", "deadass"]
            ),
            userTier: .premium
        )

        TrendingTermCard(
            term: TrendingTermResponse(
                term: "bet",
                definition: "Okay, sure, I agree",
                category: .slang,
                popularityScore: 78.2,
                searchCount: nil,
                translationCount: nil,
                firstSeen: Date().addingTimeInterval(-86400 * 3), // 3 days ago
                lastUpdated: Date(),
                isActive: true,
                exampleUsage: nil,
                origin: nil,
                relatedTerms: nil
            ),
            userTier: .free
        )
    }
    .padding()
    .background(Color(.systemGroupedBackground))
}
