// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "JobHunter",
    platforms: [
        .macOS(.v13),
    ],
    dependencies: [
        .package(url: "https://github.com/scinfu/SwiftSoup.git", from: "2.7.0"),
    ],
    targets: [
        .executableTarget(
            name: "JobHunter",
            dependencies: [
                .product(name: "SwiftSoup", package: "SwiftSoup"),
            ],
            linkerSettings: [
                .linkedLibrary("z"),
            ]
        ),
    ]
)
