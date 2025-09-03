import SwiftUI

struct MainTabView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            TranslationView()
                .tabItem {
                    Image(systemName: "text.bubble")
                    Text("Translate")
                }
                .tag(0)

            ProfileView()
                .tabItem {
                    Image(systemName: "person.circle")
                    Text("Profile")
                }
                .tag(1)
        }
        .accentColor(.lingiblePrimary)
    }
}

#Preview {
    MainTabView()
}
