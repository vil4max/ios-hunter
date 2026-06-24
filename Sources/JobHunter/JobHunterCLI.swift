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

            for source in sources {
                do {
                    let jobs = try await source.fetchJobs()
                    fputs("[\(source.company)] \(jobs.count) iOS job(s)\n", stderr)

                    for job in jobs {
                        guard !store.contains(url: job.url) else { continue }
                        try store.insert(url: job.url)
                        try await Telegram.notify(job: job)
                        newJobsCount += 1
                    }
                } catch {
                    fputs("[\(source.company)] error: \(error)\n", stderr)
                }
            }

            fputs("Done. New jobs: \(newJobsCount)\n", stderr)
        } catch {
            fputs("Fatal error: \(error)\n", stderr)
            exit(1)
        }
    }
}
