import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var appCoordinator: AppCoordinator
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            TranslationView()
                .tabItem {
                    Image(systemName: "text.bubble")
                    Text("Translate")
                }
                .tag(0)

            TrendingView(
                trendingService: TrendingService(authenticationService: appCoordinator.authenticationService),
                userService: appCoordinator.userService,
                authenticationService: appCoordinator.authenticationService
            )
                .tabItem {
                    Image(systemName: "chart.line.uptrend.xyaxis")
                    Text("Trending")
                }
                .tag(1)

            ProfileView()
                .tabItem {
                    Image(systemName: "person.circle")
                    Text("Profile")
                }
                .tag(2)
        }
        .accentColor(.lingiblePrimary)
    }
}

#Preview {
    MainTabView()
        .environmentObject(AppCoordinator())
}
