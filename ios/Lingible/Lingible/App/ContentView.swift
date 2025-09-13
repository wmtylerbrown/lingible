import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator

    var body: some View {
        Group {
            switch appCoordinator.currentState {
            case .splash:
                SplashView(isLoading: !appCoordinator.isUserDataLoaded)
            case .unauthenticated:
                AuthenticationView()
            case .authenticated:
                MainTabView()
            }
        }
        .animation(.easeInOut(duration: 0.3), value: appCoordinator.currentState)
        .onAppear {
            // Only check authentication status if we're not already authenticated
            // This prevents the splash screen from appearing when dismissing ads
            if appCoordinator.currentState == .splash {
                appCoordinator.checkAuthenticationStatus()
            }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppCoordinator())
}
