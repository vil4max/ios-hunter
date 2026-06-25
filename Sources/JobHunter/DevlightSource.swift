import Foundation
import SwiftSoup

struct DevlightSource: JobSource {
    let company = "Devlight"
    let tier: JobSourceTier = .tier3
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://devlight.io/")!
        let url = URL(string: "https://devlight.io/careers/")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let links = try document.select("a[href*=/careers/]")
        var jobs: [Job] = []
        var seen = Set<String>()

        for link in links {
            let href = try link.attr("href")
            guard href.contains("/careers/"),
                  href != "/careers/",
                  href != "https://devlight.io/careers/",
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
        url.split(separator: "/").filter { !$0.isEmpty }.last?
            .replacingOccurrences(of: "-", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? url
    }
}
