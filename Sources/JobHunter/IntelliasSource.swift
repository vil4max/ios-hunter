import Foundation

struct IntelliasSource: JobSource {
    let company = "Intellias"
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://career.intellias.com/")!
        let url = URL(string: "https://career.intellias.com/?s=iOS")!
        let html = try await http.fetchString(from: url)
        let pattern = #"<a[^>]+href="(https://career\.intellias\.com/vacancy/[^"]+)"[^>]*>([^<]{5,120})</a>"#

        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var jobs: [Job] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match,
                  let urlRange = Range(match.range(at: 1), in: html),
                  let titleRange = Range(match.range(at: 2), in: html)
            else { return }

            let jobURL = String(html[urlRange])
            let title = String(html[titleRange]).trimmingCharacters(in: .whitespacesAndNewlines)
            guard isIOSJob(title: title) else { return }
            _ = baseURL
            jobs.append(Job(title: title, url: jobURL, company: company))
        }

        return jobs
    }
}
