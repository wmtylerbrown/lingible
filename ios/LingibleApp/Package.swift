// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "Lingible",
    platforms: [
        .iOS(.v15)
    ],
    products: [
        .library(
            name: "Lingible",
            targets: ["Lingible"]
        ),
    ],
    dependencies: [
        // AWS Amplify for Cognito
        .package(url: "https://github.com/aws-amplify/amplify-swift.git", from: "2.0.0"),
        // Generated API Client (local dependency)
        .package(path: "../generated/LingibleAPI")
    ],
    targets: [
        .target(
            name: "Lingible",
            dependencies: [
                .product(name: "Amplify", package: "amplify-swift"),
                .product(name: "AWSCognitoAuthPlugin", package: "amplify-swift"),
                .product(name: "LingibleAPI", package: "LingibleAPI")
            ]
        ),
        .testTarget(
            name: "LingibleTests",
            dependencies: ["Lingible"]
        ),
    ]
)
