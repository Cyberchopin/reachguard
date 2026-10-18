import SwiftUI

@main
struct ReachGatewayApp: App {
    @StateObject private var model = GatewayModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
                .task { model.start() }
        }
        .onChange(of: scenePhase) { phase in
            // Foreground-only gateway: keep the screen awake while it is in use.
            UIApplication.shared.isIdleTimerDisabled = phase == .active
        }
    }
}
