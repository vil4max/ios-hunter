import Foundation

@main
struct JobHunterCLI {
    static func main() async {
        let databasePath = ProcessInfo.processInfo.environment["JOBS_DB_PATH"] ?? "data/jobs.sqlite"

        do {
            let store = try Store(path: databasePath)
            let http = HTTPClient()
            let sources = JobSources.all(http: http)
            var newJobsCount = 0
            var openVacancyCount = 0
            var failedSourceCount = 0

            for source in sources {
                do {
                    let jobs = try await source.fetchJobs()
                    openVacancyCount += jobs.count
                    fputs("[\(source.company)] \(jobs.count) iOS job(s)\n", stderr)

                    for job in jobs {
                        guard !store.contains(url: job.url) else { continue }
                        try store.insert(url: job.url)
                        try await Telegram.notify(job: job)
                        newJobsCount += 1
                    }
                } catch {
                    failedSourceCount += 1
                    fputs("[\(source.company)] error: \(error)\n", stderr)
                }
            }

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
