import Foundation
import SwiftSoup

struct QAreaSource: JobSource {
    let company = "QArea"
    let tier: JobSourceTier = .tier2
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://qarea.com/")!
        let url = URL(string: "https://qarea.com/careers")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let items = try document.select("a.vacancies-item")
        var jobs: [Job] = []

        for item in items {
            let href = try item.attr("href")
            guard let absolute = HTMLHelpers.absoluteURL(href, base: baseURL) else { continue }

            let primaryTitle = try item.select(".vacancies-item-title .item-title").first()?
                .text()
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            let title = primaryTitle.isEmpty
                ? try item.text().trimmingCharacters(in: .whitespacesAndNewlines)
                : primaryTitle
            guard isIOSJob(title: title) else { continue }
            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}
