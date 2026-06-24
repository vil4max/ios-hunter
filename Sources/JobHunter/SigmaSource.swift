import Foundation
import SwiftSoup

struct SigmaSource: JobSource {
    let company = "Sigma Software"
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://career.sigma.software/")!
        let url = URL(string: "https://career.sigma.software/?s=iOS")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let links = try document.select("a[href*=/vacancy/]")
        var jobs: [Job] = []
        var seen = Set<String>()

        for link in links {
            let href = try link.attr("href")
            guard let absolute = HTMLHelpers.absoluteURL(href, base: baseURL),
                  seen.insert(absolute).inserted
            else { continue }

            let title = try link.select("h3").first()?.text().trimmingCharacters(in: .whitespacesAndNewlines)
                ?? link.text().trimmingCharacters(in: .whitespacesAndNewlines)
            guard !title.isEmpty, isIOSJob(title: title) else { continue }
            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}
