import Foundation

enum SkillsExtractor {
    private static let keywords: [String: [String]] = [
        "SwiftUI": ["swiftui", "swift ui"],
        "UIKit": ["uikit", "ui kit"],
        "Combine": ["combine"],
        "Concurrency": ["async/await", "swift concurrency", "actors"],
        "GraphQL": ["graphql"],
        "Firebase": ["firebase"],
        "AI": ["core ml", "apple intelligence", "machine learning", "llm", " ai"],
        "VisionOS": ["visionos", "vision pro"],
        "watchOS": ["watchos", "watch os"],
        "Swift Testing": ["swift testing", "xctest"],
    ]

    static func detect(in text: String) -> [String] {
        let lowered = text.lowercased()
        return keywords.compactMap { skill, terms in
            terms.contains(where: { lowered.contains($0) }) ? skill : nil
        }
    }
}
