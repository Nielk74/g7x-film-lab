// swift-tools-version: 5.9
import Foundation
import PackageDescription

let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
let engine = ProcessInfo.processInfo.environment["FOTUFILM_SOURCE"]
    ?? root.appendingPathComponent("../../.cache/fotufilm-engine").standardized.path
let package = Package(
    name: "G7XFilmBake",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "film-bake", targets: ["FilmBake"])],
    dependencies: [.package(name: "Fotufilm", path: engine)],
    targets: [.executableTarget(name: "FilmBake", dependencies: [
        .product(name: "FotufilmCore", package: "Fotufilm")
    ])]
)
