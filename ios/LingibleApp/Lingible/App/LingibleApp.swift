import SwiftUI
import Amplify
import AWSCognitoAuthPlugin

@main
struct LingibleApp: App {
    @StateObject private var appCoordinator = AppCoordinator()

    init() {
        configureAmplify()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appCoordinator)
                .preferredColorScheme(.light) // For now, we'll use light mode
        }
    }

    private func configureAmplify() {
        do {
            // Configure Amplify with Cognito
            try Amplify.add(plugin: AWSCognitoAuthPlugin())
            try Amplify.configure()
            print("✅ Amplify configured successfully")
        } catch {
            print("❌ Failed to configure Amplify: \(error)")
        }
    }
}
