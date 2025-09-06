import SwiftUI
import GoogleMobileAds

// MARK: - Banner Ad View
struct BannerAdView: UIViewRepresentable {
    let adUnitID: String
    @Binding var isLoaded: Bool
    
    func makeUIView(context: Context) -> GADBannerView {
        let bannerView = GADBannerView(adSize: GADAdSizeBanner)
        bannerView.adUnitID = adUnitID
        bannerView.delegate = context.coordinator
        bannerView.rootViewController = UIApplication.shared.windows.first?.rootViewController
        
        // Load the ad
        let request = GADRequest()
        bannerView.load(request)
        
        return bannerView
    }
    
    func updateUIView(_ uiView: GADBannerView, context: Context) {
        // Update if needed
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, GADBannerViewDelegate {
        let parent: BannerAdView
        
        init(_ parent: BannerAdView) {
            self.parent = parent
        }
        
        func bannerViewDidReceiveAd(_ bannerView: GADBannerView) {
            print("✅ BannerAdView: Ad loaded successfully")
            DispatchQueue.main.async {
                self.parent.isLoaded = true
            }
        }
        
        func bannerView(_ bannerView: GADBannerView, didFailToReceiveAdWithError error: Error) {
            print("❌ BannerAdView: Failed to load ad: \(error.localizedDescription)")
            DispatchQueue.main.async {
                self.parent.isLoaded = false
            }
        }
        
        func bannerViewDidRecordImpression(_ bannerView: GADBannerView) {
            print("📊 BannerAdView: Ad impression recorded")
        }
        
        func bannerViewWillPresentScreen(_ bannerView: GADBannerView) {
            print("👆 BannerAdView: Ad will present screen")
        }
        
        func bannerViewWillDismissScreen(_ bannerView: GADBannerView) {
            print("👆 BannerAdView: Ad will dismiss screen")
        }
        
        func bannerViewDidDismissScreen(_ bannerView: GADBannerView) {
            print("👆 BannerAdView: Ad did dismiss screen")
        }
    }
}

// MARK: - SwiftUI Wrapper for Banner Ad
struct SwiftUIBannerAd: View {
    let adUnitID: String
    @State private var isLoaded = false
    @State private var showAd = true
    
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
                // Small delay to ensure smooth loading
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                    showAd = true
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
