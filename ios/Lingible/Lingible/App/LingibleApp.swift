import SwiftUI
import Amplify
import AWSCognitoAuthPlugin
import GoogleMobileAds
import AppTrackingTransparency

@main
struct LingibleApp: App {
    @StateObject private var appCoordinator = AppCoordinator()
    @StateObject private var attManager = AppTrackingTransparencyManager()
    @State private var showATTPermission = false

    init() {
        configureAmplify()
        configureAPI()
        configureAdMob()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appCoordinator)
                .environmentObject(attManager)
                .preferredColorScheme(selectedColorScheme)
                .onAppear {
                    checkATTPermission()
                }
                .sheet(isPresented: $showATTPermission) {
                    attManager.createPermissionRequestView()
                }
        }
    }

    // MARK: - Theme Support
    @AppStorage("selectedTheme") private var selectedTheme = "system"

    private var selectedColorScheme: ColorScheme? {
        switch selectedTheme {
        case "light":
            return .light
        case "dark":
            return .dark
        default:
            return nil // Use system default
        }
    }

    private func configureAmplify() {
        do {
            print("🔧 Starting Amplify Gen 2 configuration...")
            print("🔧 Current environment: \(AppConfiguration.currentEnvironment.displayName)")

            // Configure Amplify with Cognito (Gen 2 approach)
            try Amplify.add(plugin: AWSCognitoAuthPlugin())
            print("✅ AWSCognitoAuthPlugin added successfully")

            // Use Gen 2 configuration - the build process should have copied the correct file to amplify_outputs.json
            print("🔧 Configuring Amplify with Gen 2 outputs...")
            try Amplify.configure(with: .amplifyOutputs)
            print("✅ Amplify configured successfully with Gen 2 configuration")

        } catch {
            print("❌ Failed to configure Amplify: \(error)")
            print("🔍 Error details:")
            print("  - Error type: \(type(of: error))")
            print("  - Error description: \(error.localizedDescription)")
            if let nsError = error as NSError? {
                print("  - Error domain: \(nsError.domain)")
                print("  - Error code: \(nsError.code)")
                print("  - User info: \(nsError.userInfo)")
            }
        }
    }

    private func configureAPI() {
        AppConfiguration.configureAPI()
    }

    private func configureAdMob() {
        print("🔧 LingibleApp: Configuring AdMob...")
        AdMobConfig.initializeWithATT()
        AdMobConfig.configureTestDevices()
    }

    private func checkATTPermission() {
        // Check if we need to show ATT permission request
        if attManager.shouldShowPermissionRequest {
            // Delay the presentation slightly to ensure the app is fully loaded
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                showATTPermission = true
            }
        }
    }
}
