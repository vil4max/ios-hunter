import Foundation
import SwiftSoup

struct MWDNSource: JobSource {
    let company = "MWDN"
    let tier: JobSourceTier = .tier2
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://jobs.mwdn.com/")!
        let url = URL(string: "https://jobs.mwdn.com/careers/")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let items = try document.select("a.comeet-position")
        var jobs: [Job] = []
        var seenSlugs = Set<String>()

        for item in items {
            let href = try item.attr("href")
            guard let absolute = HTMLHelpers.absoluteURL(href, base: baseURL) else { continue }

            let slug = absolute
                .split(separator: "/")
                .dropLast()
                .last
                .map(String.init) ?? absolute
            guard seenSlugs.insert(slug).inserted else { continue }

            let title = try item.select(".comeet-position-name").first()?
                .text()
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            guard isIOSJob(title: title) else { continue }
            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}
