import Foundation

enum DiffEngine {
    static func lineDiff(old: String?, new: String?) -> String {
        let oldLines = (old ?? "").split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
        let newLines = (new ?? "").split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
        var result: [String] = []

        let oldSet = Set(oldLines)
        let newSet = Set(newLines)
        for line in newLines where !oldSet.contains(line) && !line.isEmpty {
            result.append("+ \(line)")
        }
        for line in oldLines where !newSet.contains(line) && !line.isEmpty {
            result.append("- \(line)")
        }
        return result.joined(separator: "\n")
    }

    static func summarize(_ diff: String) -> String {
        let added = diff.split(separator: "\n").filter { $0.hasPrefix("+ ") }.prefix(3)
        return added.map { String($0.dropFirst(2)) }.joined(separator: ", ")
    }
}
