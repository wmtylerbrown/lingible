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
            print("✅ BannerAdView: Set root view controller successfully")
        } else {
            print("❌ BannerAdView: Failed to get root view controller")
        }
        
        // Load the ad
        let request = Request()
        bannerView.load(request)
        print("🔄 BannerAdView: Loading ad with unit ID: \(adUnitID)")
        
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
            print("✅ BannerAdView: Ad loaded successfully")
            DispatchQueue.main.async {
                self.parent.isLoaded = true
            }
        }
        
        func bannerView(_ bannerView: BannerView, didFailToReceiveAdWithError error: Error) {
            print("❌ BannerAdView: Failed to load ad: \(error.localizedDescription)")
            DispatchQueue.main.async {
                self.parent.isLoaded = false
            }
        }
        
        func bannerViewDidRecordImpression(_ bannerView: BannerView) {
            print("📊 BannerAdView: Ad impression recorded")
        }
        
        func bannerViewWillPresentScreen(_ bannerView: BannerView) {
            print("👆 BannerAdView: Ad will present screen")
        }
        
        func bannerViewWillDismissScreen(_ bannerView: BannerView) {
            print("👆 BannerAdView: Ad will dismiss screen")
        }
        
        func bannerViewDidDismissScreen(_ bannerView: BannerView) {
            print("👆 BannerAdView: Ad did dismiss screen")
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
                    print("🔄 SwiftUIBannerAd: Banner ad view appeared")
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
