import Foundation

enum ReportGenerator {
    static func weeklyReport(repository: JobRepository) -> String {
        let calendar = Calendar.current
        let week = calendar.component(.weekOfYear, from: Date())
        let year = calendar.component(.yearForWeekOfYear, from: Date())
        let remoteCounts = repository.countByRemote()
        let newJobs = repository.historyCount(field: "created", sinceDays: 7)
        let closedJobs = repository.historyCount(field: "status", sinceDays: 7)
        let stats = CompanyStats.compute(repository: repository).prefix(10)

        var lines = [
            "# iOS Market Report — \(year)-week-\(String(format: "%02d", week))",
            "",
            "## Summary",
            "- New jobs: \(newJobs)",
            "- Closed jobs: \(closedJobs)",
            "- Open jobs: \(repository.openJobCount())",
            "- Remote: \(remoteCounts.remote) | Hybrid: \(remoteCounts.hybrid) | Onsite: \(remoteCounts.onsite)",
            "",
            "## Top hirers",
            "",
            "| Company | Open | This year | Avg lifetime |",
            "| --- | ---: | ---: | ---: |",
        ]

        for stat in stats {
            lines.append(
                "| \(stat.company) | \(stat.openJobs) open | \(stat.jobsThisYear) this year | \(Int(stat.averageLifetimeDays))d avg |"
            )
        }

        return lines.joined(separator: "\n")
    }
}
