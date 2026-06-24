import Foundation

struct NixSource: JobSource {
    let company = "N-iX"
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://careers.n-ix.com/jobs/?keyword=ios&work_type%5B%5D=Remote&work_type%5B%5D=Office+based")!
        let html = try await http.fetchString(from: url)
        let pattern = #"<a[^>]+href="([^"]+)"[^>]*>\s*([^<]+\(#\d+\))\s*</a>"#

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

            let href = String(html[urlRange])
            let title = String(html[titleRange]).trimmingCharacters(in: .whitespacesAndNewlines)
            guard let absolute = HTMLHelpers.absoluteURL(href, base: url),
                  isIOSJob(title: title)
            else { return }

            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}
