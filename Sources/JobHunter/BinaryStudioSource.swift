import Foundation

struct BinaryStudioSource: JobSource {
    let company = "Binary Studio"
    let tier: JobSourceTier = .tier2
    private let listURL = URL(string: "https://binary-studio.com/careers/")!
    private let pattern = #"https://binary-studio\.com/careers/([a-z0-9-]+)/"#
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        guard let html = try await http.fetchStringAllowingBotWall(from: listURL) else {
            fputs("[\(company)] careers page blocked by bot wall; treating as empty\n", stderr)
            return []
        }

        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var seen = Set<String>()
        var jobs: [Job] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match,
                  let urlRange = Range(match.range, in: html)
            else { return }

            let jobURL = String(html[urlRange])
            guard seen.insert(jobURL).inserted else { return }

            let slugRange = Range(match.range(at: 1), in: html)
            let title = slugRange.map { String(html[$0]).replacingOccurrences(of: "-", with: " ") } ?? jobURL
            guard isIOSJob(title: title) else { return }
            jobs.append(Job(title: title, url: jobURL, company: company))
        }

        return jobs
    }
}
