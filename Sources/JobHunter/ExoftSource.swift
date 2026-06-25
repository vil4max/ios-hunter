import Foundation
import SwiftSoup

struct ExoftSource: JobSource {
    let company = "Exoft"
    let tier: JobSourceTier = .tier2
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://www.exoft.net/")!
        let url = URL(string: "https://www.exoft.net/career/")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let links = try document.select("a[href*=/career/]")
        var jobs: [Job] = []
        var seen = Set<String>()

        for link in links {
            let href = try link.attr("href")
            guard href.contains("/career/"),
                  href != "/career/",
                  href != "https://www.exoft.net/career/",
                  let absolute = HTMLHelpers.absoluteURL(href, base: baseURL),
                  seen.insert(absolute).inserted
            else { continue }

            let title = try link.text().trimmingCharacters(in: .whitespacesAndNewlines)
            let resolvedTitle = title.isEmpty
                ? absolute.split(separator: "/").last?
                    .replacingOccurrences(of: "-", with: " ")
                    .trimmingCharacters(in: .whitespacesAndNewlines) ?? absolute
                : title
            guard isIOSJob(title: resolvedTitle) else { continue }
            jobs.append(Job(title: resolvedTitle, url: absolute, company: company))
        }

        return jobs
    }
}
