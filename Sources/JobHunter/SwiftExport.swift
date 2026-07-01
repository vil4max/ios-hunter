import Foundation

enum SwiftExport {
    static func write(jobs: [Job], to path: String) throws {
        let directory = (path as NSString).deletingLastPathComponent
        if !directory.isEmpty {
            try FileManager.default.createDirectory(
                atPath: directory,
                withIntermediateDirectories: true
            )
        }

        let payload: [[String: String?]] = jobs.map { job in
            [
                "company": job.company,
                "title": job.title,
                "url": job.url,
                "source": job.source.rawValue,
                "location": job.location,
                "remote": job.remote?.rawValue,
                "description": job.description,
                "hash": job.hash,
            ]
        }

        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        let url = URL(fileURLWithPath: path)
        try data.write(to: url, options: .atomic)
    }
}
