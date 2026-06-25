import Foundation
import SwiftSoup

struct SoftjournSource: JobSource {
    let company = "Softjourn"
    let tier: JobSourceTier = .tier3
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://softjourn.com/")!
        let url = URL(string: "https://softjourn.com/careers")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let links = try document.select("a[href*=/careers/vacancies/]")
        var jobs: [Job] = []
        var seen = Set<String>()

        for link in links {
            let href = try link.attr("href")
            guard href.contains("/careers/vacancies/"),
                  href != "/careers/vacancies",
                  href != "/careers/vacancies/",
                  let absolute = HTMLHelpers.absoluteURL(href, base: baseURL),
                  seen.insert(absolute).inserted
            else { continue }

            let title = try link.text().trimmingCharacters(in: .whitespacesAndNewlines)
            let resolvedTitle = title.isEmpty ? titleFromURL(absolute) : title
            guard isIOSJob(title: resolvedTitle) else { continue }
            jobs.append(Job(title: resolvedTitle, url: absolute, company: company))
        }

        return jobs
    }

    private func titleFromURL(_ url: String) -> String {
        url.split(separator: "/").last?
            .replacingOccurrences(of: "-", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? url
    }
}
