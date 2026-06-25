import Foundation
import SwiftSoup

struct DevProSource: JobSource {
    let company = "Dev.Pro"
    let tier: JobSourceTier = .tier1
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://career.dev.pro/")!
        let url = URL(string: "https://career.dev.pro/vacancies/")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let links = try document.select("a.vacancy_details")
        var jobs: [Job] = []
        var seen = Set<String>()

        for link in links {
            let href = try link.attr("href")
            guard let absolute = HTMLHelpers.absoluteURL(href, base: baseURL),
                  seen.insert(absolute).inserted
            else { continue }

            let title = try link.text().trimmingCharacters(in: .whitespacesAndNewlines)
            guard isIOSJob(title: title) else { continue }
            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}
