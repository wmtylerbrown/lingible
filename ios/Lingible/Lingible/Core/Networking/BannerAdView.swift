import SwiftUI
import GoogleMobileAds

// MARK: - Banner Ad View
struct BannerAdView: UIViewRepresentable {
    let adUnitID: String
    @Binding var isLoaded: Bool

    func makeUIView(context: Context) -> BannerView {
        print("🟡 AdMob Banner: Creating banner view with unit ID: \(adUnitID)")

        // Use standard banner size initially, then switch to adaptive after layout
        let bannerView = BannerView(adSize: AdSizeBanner)
        bannerView.adUnitID = adUnitID
        bannerView.delegate = context.coordinator

        // Get the root view controller properly with better error handling
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
           let window = windowScene.windows.first,
           let rootViewController = window.rootViewController {
            bannerView.rootViewController = rootViewController
            print("🟡 AdMob Banner: Root view controller set successfully")
        } else {
            print("🔴 AdMob Banner: Failed to get root view controller")
        }

        // Load the ad with ATT-aware configuration
        print("🟡 AdMob Banner: Loading ad with unit ID: \(adUnitID)")
        let request = AdMobConfig.createGADRequest()
        bannerView.load(request)

        return bannerView
    }

    func updateUIView(_ uiView: BannerView, context: Context) {
        // Update banner size to adaptive after layout
        DispatchQueue.main.async {
            let screenWidth = UIScreen.main.bounds.width
            let adSize = currentOrientationAnchoredAdaptiveBanner(width: screenWidth - 40) // Account for padding
            uiView.adSize = adSize
            print("🟡 AdMob Banner: Updated to adaptive size with width: \(screenWidth - 40)")
        }
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
            print("🟢 AdMob Banner: Ad loaded successfully")
            DispatchQueue.main.async {
                self.parent.isLoaded = true
            }
        }

        func bannerView(_ bannerView: BannerView, didFailToReceiveAdWithError error: Error) {
            print("🔴 AdMob Banner: Failed to load ad - \(error.localizedDescription)")
            print("🔴 AdMob Banner: Error details: \(error)")
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
                BannerAdView(adUnitID: adUnitID, isLoaded: $isLoaded)
                    .frame(height: 50) // Standard banner height initially
                    .opacity(isLoaded ? 1.0 : 0.3) // Show with reduced opacity while loading
                    .overlay(
                        // Show loading indicator when not loaded
                        Group {
                            if !isLoaded {
                                HStack {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                    Text("Loading ad...")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                .background(Color.white.opacity(0.8))
                                .cornerRadius(4)
                            }
                        }
                    )
                    .transition(.opacity)
            }
            .onAppear {
                print("🟡 AdMob Banner: SwiftUIBannerAd appeared, hasAppeared: \(hasAppeared)")
                if !hasAppeared {
                    hasAppeared = true
                    print("🟡 AdMob Banner: Banner view created and ready")
                }
            }
        } else {
            Text("Banner not showing")
                .foregroundColor(.red)
                .onAppear {
                    print("🔴 AdMob Banner: Banner not showing - showAd: \(showAd)")
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
