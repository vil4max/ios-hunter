import Foundation

enum SwiftExport {
    struct Meta: Sendable {
        let sourcesTotal: Int
        let sourcesFailed: Int
        let failedCompanies: [String]
    }

    static func write(jobs: [Job], meta: Meta, to path: String) throws {
        let directory = (path as NSString).deletingLastPathComponent
        if !directory.isEmpty {
            try FileManager.default.createDirectory(
                atPath: directory,
                withIntermediateDirectories: true
            )
        }

        let jobPayload: [[String: String?]] = jobs.map { job in
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

        let payload: [String: Any] = [
            "meta": [
                "sources_total": meta.sourcesTotal,
                "sources_failed": meta.sourcesFailed,
                "failed_companies": meta.failedCompanies,
            ],
            "jobs": jobPayload,
        ]

        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        let url = URL(fileURLWithPath: path)
        try data.write(to: url, options: .atomic)
    }
}
