import SwiftUI
import GoogleMobileAds

// MARK: - Banner Ad View
struct BannerAdView: UIViewRepresentable {
    let adUnitID: String
    @Binding var isLoaded: Bool

    func makeUIView(context: Context) -> BannerView {
        let bannerView = BannerView(adSize: AdSizeBanner)
        bannerView.adUnitID = adUnitID
        bannerView.delegate = context.coordinator

        // Get the root view controller properly with better error handling
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootViewController = window.rootViewController {
            bannerView.rootViewController = rootViewController
        }

        // Load the ad with ATT-aware configuration
        let request = AdMobConfig.createGADRequest()
        bannerView.load(request)

        return bannerView
    }

    func updateUIView(_ uiView: BannerView, context: Context) {
        // Update if needed
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, BannerViewDelegate {
        let parent: BannerAdView

        init(_ parent: BannerAdView) {
            self.parent = parent
        }

        func bannerViewDidReceiveAd(_ bannerView: BannerView) {
            DispatchQueue.main.async {
                self.parent.isLoaded = true
            }
        }

        func bannerView(_ bannerView: BannerView, didFailToReceiveAdWithError error: Error) {
            DispatchQueue.main.async {
                self.parent.isLoaded = false
            }
        }

        func bannerViewDidRecordImpression(_ bannerView: BannerView) {
        }

        func bannerViewWillPresentScreen(_ bannerView: BannerView) {
        }

        func bannerViewWillDismissScreen(_ bannerView: BannerView) {
        }

        func bannerViewDidDismissScreen(_ bannerView: BannerView) {
        }
    }
}

// MARK: - SwiftUI Wrapper for Banner Ad
struct SwiftUIBannerAd: View {
    let adUnitID: String
    @State private var isLoaded = false
    @State private var showAd = true
    @State private var hasAppeared = false

    var body: some View {
        if showAd {
            VStack {
                if isLoaded {
                    BannerAdView(adUnitID: adUnitID, isLoaded: $isLoaded)
                        .frame(height: 50) // Standard banner height
                        .transition(.opacity)
                } else {
                    // Placeholder while ad loads
                    Rectangle()
                        .fill(Color.gray.opacity(0.1))
                        .frame(height: 50)
                        .overlay(
                            HStack {
                                ProgressView()
                                    .scaleEffect(0.8)
                                Text("Loading ad...")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        )
                }
            }
            .onAppear {
                if !hasAppeared {
                    hasAppeared = true
                    // Small delay to ensure the view controller is ready
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        showAd = true
                    }
                }
            }
        }
    }
}

// MARK: - Preview
#Preview {
    VStack {
        Text("App Content")
            .padding()

        SwiftUIBannerAd(adUnitID: AdMobConfig.bannerAdUnitID)

        Text("More App Content")
            .padding()
    }
    .onAppear {
        AdMobConfig.initialize()
    }
}
