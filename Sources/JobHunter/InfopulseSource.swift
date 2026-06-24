import Foundation

struct InfopulseSource: JobSource {
    let company = "Infopulse"
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://careers.tieto.com/")!
        let url = URL(string: "https://careers.tieto.com/jobs?q=iOS")!
        let html = try await http.fetchString(from: url)
        let pattern = #"<a[^>]+href="(/job/[^"]+)"[^>]*>([^<]{5,120})</a>"#

        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var seen = Set<String>()
        var jobs: [Job] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match,
                  let urlRange = Range(match.range(at: 1), in: html),
                  let titleRange = Range(match.range(at: 2), in: html)
            else { return }

            let href = String(html[urlRange])
            let title = String(html[titleRange]).trimmingCharacters(in: .whitespacesAndNewlines)
            guard title != "Apply",
                  let absolute = HTMLHelpers.absoluteURL(href, base: baseURL),
                  seen.insert(absolute).inserted,
                  isIOSJob(title: title)
            else { return }

            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}
