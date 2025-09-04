import SwiftUI
import Amplify
import AWSCognitoAuthPlugin

@main
struct LingibleApp: App {
    @StateObject private var appCoordinator = AppCoordinator()

    init() {
        configureAmplify()
        configureAPI()
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
            print("🔧 Starting Amplify Gen 2 configuration...")

            // Configure Amplify with Cognito (Gen 2 approach)
            try Amplify.add(plugin: AWSCognitoAuthPlugin())
            print("✅ AWSCognitoAuthPlugin added successfully")

            // Use Gen 2 configuration with amplify_outputs.json
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
}
