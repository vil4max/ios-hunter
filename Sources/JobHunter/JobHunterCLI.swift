import Foundation

@main
struct JobHunterCLI {
    static func main() async {
        let exportPath = ProcessInfo.processInfo.environment["SWIFT_EXPORT_PATH"] ?? "database/swift_export.json"

        let http = HTTPClient()
        let sources = JobSources.all(http: http)
        var fetchedJobs: [Job] = []
        var failedSourceCount = 0

        for source in sources {
            do {
                let jobs = try await source.fetchJobs()
                fetchedJobs.append(contentsOf: jobs)
                fputs("[\(source.company)] \(jobs.count) iOS job(s)\n", stderr)
            } catch {
                failedSourceCount += 1
                fputs("[\(source.company)] error: \(error)\n", stderr)
            }
        }

        let (uniqueJobs, duplicatesRemoved) = Deduplicator.unique(jobs: fetchedJobs)
        fputs(
            "Fetched: \(fetchedJobs.count), unique: \(uniqueJobs.count), duplicates removed: \(duplicatesRemoved)\n",
            stderr
        )
        fputs("Sources OK: \(sources.count - failedSourceCount)/\(sources.count)\n", stderr)

        do {
            try SwiftExport.write(jobs: uniqueJobs, to: exportPath)
            fputs("Exported to \(exportPath)\n", stderr)
        } catch {
            fputs("Fatal error: \(error)\n", stderr)
            exit(1)
        }
    }
}
