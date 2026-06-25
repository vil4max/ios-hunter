import Foundation

struct InnovecsSource: JobSource {
    let company = "Innovecs"
    let tier: JobSourceTier = .tier3
    private let http: HTTPClient

    private let listURL = URL(string: "https://jobs.innovecs.com/")!

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let html = try await http.fetchString(from: listURL)
        let pattern = #"https://jobs\.innovecs\.com/vacancies/(\d+)-([a-z0-9-]+)/"#

        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var seen = Set<String>()
        var jobs: [Job] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match,
                  let urlRange = Range(match.range, in: html),
                  let slugRange = Range(match.range(at: 2), in: html)
            else { return }

            let jobURL = String(html[urlRange])
            guard seen.insert(jobURL).inserted else { return }

            let slug = String(html[slugRange])
            let title = slug.replacingOccurrences(of: "-", with: " ")
            guard isIOSJob(title: title) else { return }
            jobs.append(Job(title: title, url: jobURL, company: company))
        }

        return jobs
    }
}
