import Foundation

@main
struct JobHunterCLI {
    static func main() async {
        let databasePath = ProcessInfo.processInfo.environment["JOBS_DB_PATH"] ?? "database/swift.db"
        let exportPath = ProcessInfo.processInfo.environment["SWIFT_EXPORT_PATH"] ?? "database/swift_export.json"
        let jobsJSONPath = ProcessInfo.processInfo.environment["JOBS_JSON_PATH"] ?? "database/jobs.json"
        let historyJSONPath = ProcessInfo.processInfo.environment["HISTORY_JSON_PATH"] ?? "database/history.json"
        let reportsDir = ProcessInfo.processInfo.environment["REPORTS_DIR"] ?? "reports"

        do {
            let repository = try JobRepository(path: databasePath)
            let http = HTTPClient()
            let sources = JobSources.all(http: http)
            var fetchedJobs: [Job] = []
            var failedSourceCount = 0
            var newCount = 0
            var updatedCount = 0
            var reopenedCount = 0
            var seenIDs: Set<String> = []

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
            fputs("Duplicates removed: \(duplicatesRemoved)\n", stderr)

            for job in uniqueJobs {
                let change = repository.upsert(job)
                seenIDs.insert(change.jobID)
                switch change.kind {
                case .new: newCount += 1
                case .updated: updatedCount += 1
                case .reopened: reopenedCount += 1
                case .closed, .unchanged: break
                }
            }

            let closedCount = repository.closeMissing(seenIDs: seenIDs)

            try SwiftExport.write(jobs: uniqueJobs, to: exportPath)
            try Exporter.write(jobs: repository.exportOpenJobs(), to: jobsJSONPath)
            try Exporter.writeHistory(repository.exportHistory(), to: historyJSONPath)

            let weekly = ReportGenerator.weeklyReport(repository: repository)
            let companies = CompanyStats.renderMarkdown(CompanyStats.compute(repository: repository))
            try writeText(weekly, to: "\(reportsDir)/weekly/latest.md")
            try writeText(companies, to: "\(reportsDir)/companies/index.md")

            fputs("Exported \(uniqueJobs.count) jobs to \(exportPath)\n", stderr)

            let summary = MonitorSummary(
                newJobsCount: newCount,
                updatedJobsCount: updatedCount,
                reopenedJobsCount: reopenedCount,
                closedJobsCount: closedCount,
                openVacancyCount: repository.openJobCount(),
                trackedVacancyCount: repository.trackedCount(),
                sourceCount: sources.count,
                failedSourceCount: failedSourceCount
            )
            do {
                try await Telegram.notifyCheckComplete(summary: summary)
            } catch {
                fputs("Telegram: \(error)\n", stderr)
            }

            fputs(
                "Done. New: \(newCount), Updated: \(updatedCount), Reopened: \(reopenedCount), Closed: \(closedCount)\n",
                stderr
            )
        } catch {
            fputs("Fatal error: \(error)\n", stderr)
            exit(1)
        }
    }

    private static func writeText(_ text: String, to path: String) throws {
        let directory = (path as NSString).deletingLastPathComponent
        if !directory.isEmpty {
            try FileManager.default.createDirectory(atPath: directory, withIntermediateDirectories: true)
        }
        try text.write(toFile: path, atomically: true, encoding: .utf8)
    }
}
