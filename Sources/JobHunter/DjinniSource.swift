import Foundation
import SwiftSoup

struct DjinniSource: JobSource {
    let company = "Djinni"
    let tier: JobSourceTier = .tier1
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://djinni.co/jobs/?primary_keyword=ios&exp_level=2y&exp_level=3y")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html)
        let items = try document.select("li.list-jobs__item")

        var jobs: [Job] = []
        for item in items.array() {
            guard let link = try item.select("a.job-list-item__link").first() else { continue }
            let title = try link.text()
            guard isIOSJob(title: title) else { continue }
            let href = try link.attr("href")
            let jobURL = href.hasPrefix("http") ? href : "https://djinni.co\(href)"
            let company = (try? item.select(".d-flex.align-items-center a").first()?.text()) ?? "Unknown"
            jobs.append(
                Job(
                    title: title,
                    url: jobURL,
                    company: company,
                    source: .djinni
                )
            )
        }
        return jobs
    }
}
