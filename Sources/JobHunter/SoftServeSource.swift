import Foundation

struct SoftServeSource: JobSource {
    let company = "SoftServe"
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://career.softserveinc.com/")!
        let url = URL(string: "https://career.softserveinc.com/en-us/vacancies")!
        let html = try await http.fetchString(from: url)
        let pattern = #"href="(/en-us/vacancies/[a-z0-9-]+)""#

        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var seen = Set<String>()
        var jobs: [Job] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match, let pathRange = Range(match.range(at: 1), in: html) else { return }
            let path = String(html[pathRange])
            guard !path.contains("_payload"),
                  let absolute = HTMLHelpers.absoluteURL(path, base: baseURL),
                  seen.insert(absolute).inserted
            else { return }

            let slug = path.split(separator: "/").last ?? ""
            let title = slug
                .replacingOccurrences(of: "-", with: " ")
                .replacingOccurrences(of: #"\d+$"#, with: "", options: .regularExpression)
                .trimmingCharacters(in: .whitespacesAndNewlines)

            guard isIOSJob(title: title) else { return }
            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}
