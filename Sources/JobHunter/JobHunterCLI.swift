import Foundation

@main
struct JobHunterCLI {
    static func main() async {
        let databasePath = ProcessInfo.processInfo.environment["JOBS_DB_PATH"] ?? "data/jobs.sqlite"
        let exportPath = ProcessInfo.processInfo.environment["SWIFT_EXPORT_PATH"] ?? "database/swift_export.json"

        do {
            let store = try Store(path: databasePath)
            let http = HTTPClient()
            let sources = JobSources.all(http: http)
            var newJobsCount = 0
            var openVacancyCount = 0
            var failedSourceCount = 0
            var fetchedJobs: [Job] = []

            for source in sources {
                do {
                    let jobs = try await source.fetchJobs()
                    fetchedJobs.append(contentsOf: jobs)
                    openVacancyCount += jobs.count
                    fputs("[\(source.company)] \(jobs.count) iOS job(s)\n", stderr)

                    for job in jobs {
                        guard !store.contains(url: job.url) else { continue }
                        try store.insert(url: job.url)
                        newJobsCount += 1
                    }
                } catch {
                    failedSourceCount += 1
                    fputs("[\(source.company)] error: \(error)\n", stderr)
                }
            }

            try SwiftExport.write(jobs: fetchedJobs, to: exportPath)
            fputs("Exported \(fetchedJobs.count) jobs to \(exportPath)\n", stderr)

            let summary = MonitorSummary(
                newJobsCount: newJobsCount,
                openVacancyCount: openVacancyCount,
                trackedVacancyCount: store.trackedVacancyCount(),
                sourceCount: sources.count,
                failedSourceCount: failedSourceCount
            )
            do {
                try await Telegram.notifyCheckComplete(summary: summary)
            } catch {
                fputs("Telegram: \(error)\n", stderr)
            }

            fputs("Done. New jobs: \(newJobsCount)\n", stderr)
        } catch {
            fputs("Fatal error: \(error)\n", stderr)
            exit(1)
        }
    }
}
