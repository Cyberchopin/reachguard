// swift-tools-version:5.9
// Platform-independent gateway logic. The iOS app compiles these same source
// files directly; this package exists so they can be tested with `swift test`.
import PackageDescription

let package = Package(
    name: "ReachCore",
    platforms: [.macOS(.v13), .iOS(.v16)],
    products: [.library(name: "ReachCore", targets: ["ReachCore"])],
    targets: [
        .target(name: "ReachCore"),
        .testTarget(name: "ReachCoreTests", dependencies: ["ReachCore"]),
    ]
)
