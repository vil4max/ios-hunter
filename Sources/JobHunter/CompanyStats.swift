import Foundation

struct CompanyStat: Sendable {
    let company: String
    let jobsThisYear: Int
    let openJobs: Int
    let averageLifetimeDays: Double
}

enum CompanyStats {
    static func compute(repository: JobRepository) -> [CompanyStat] {
        let year = Calendar.current.component(.year, from: Date())
        let start = "\(year)-01-01"
        var stats: [CompanyStat] = []

        let companies = repository.exportOpenJobs().compactMap { $0["company"] }
        let unique = Set(companies)
        for company in unique.sorted() {
            let jobsThisYear = repository.countJobs(company: company, since: start)
            let openJobs = repository.countOpenJobs(company: company)
            let avgLifetime = repository.averageLifetimeDays(company: company)
            stats.append(
                CompanyStat(
                    company: company,
                    jobsThisYear: jobsThisYear,
                    openJobs: openJobs,
                    averageLifetimeDays: avgLifetime
                )
            )
        }
        return stats.sorted { $0.openJobs > $1.openJobs }
    }

    static func renderMarkdown(_ stats: [CompanyStat]) -> String {
        var lines = ["# Company Statistics", ""]
        for stat in stats.prefix(20) {
            lines.append("## \(stat.company)")
            lines.append("- Jobs this year: \(stat.jobsThisYear)")
            lines.append("- Currently open: \(stat.openJobs)")
            lines.append("- Average lifetime: \(Int(stat.averageLifetimeDays)) days")
            lines.append("")
        }
        return lines.joined(separator: "\n")
    }
}
