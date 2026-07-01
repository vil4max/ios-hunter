import Foundation

enum Exporter {
    static func write(jobs: [[String: String]], to path: String) throws {
        try writeJSON(jobs, to: path)
    }

    static func writeHistory(_ history: [[String: String]], to path: String) throws {
        try writeJSON(history, to: path)
    }

    private static func writeJSON(_ payload: Any, to path: String) throws {
        let directory = (path as NSString).deletingLastPathComponent
        if !directory.isEmpty {
            try FileManager.default.createDirectory(atPath: directory, withIntermediateDirectories: true)
        }
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: URL(fileURLWithPath: path), options: .atomic)
    }
}
