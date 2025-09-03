import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator

    var body: some View {
        Group {
            switch appCoordinator.currentState {
            case .splash:
                SplashView()
            case .unauthenticated:
                AuthenticationView()
            case .authenticated:
                MainTabView()
            }
        }
        .animation(.easeInOut(duration: 0.3), value: appCoordinator.currentState)
        .onAppear {
            appCoordinator.checkAuthenticationStatus()
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppCoordinator())
}
