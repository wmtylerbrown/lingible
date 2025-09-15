import SwiftUI
import Amplify
import AWSCognitoAuthPlugin
import GoogleMobileAds
import AppTrackingTransparency

@main
struct LingibleApp: App {
    @StateObject private var attManager = AppTrackingTransparencyManager()
    @StateObject private var appCoordinator: AppCoordinator

    init() {
        // Initialize ATT manager first
        let attManager = AppTrackingTransparencyManager()
        self._attManager = StateObject(wrappedValue: attManager)

        // Initialize app coordinator with ATT manager
        self._appCoordinator = StateObject(wrappedValue: AppCoordinator(authenticationService: AuthenticationService(), userService: UserService(authenticationService: AuthenticationService()), attManager: attManager))

        // Configure services
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
                    // ATT permission will now be requested after authentication
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

            // Configure Amplify with Cognito (Gen 2 approach)
            try Amplify.add(plugin: AWSCognitoAuthPlugin())

            // Use Gen 2 configuration - the build process should have copied the correct file to amplify_outputs.json
            try Amplify.configure(with: .amplifyOutputs)

        } catch {
            // Log error but don't crash the app
            print("Failed to configure Amplify: \(error.localizedDescription)")
        }
    }

    private func configureAPI() {
        AppConfiguration.configureAPI()
    }

    private func configureAdMob() {
        AdMobConfig.initializeWithATT()
        #if DEBUG
        AdMobConfig.configureTestDevices()
        #endif
    }

}
