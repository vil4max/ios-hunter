import Foundation
import SwiftSoup

struct DOUSource: JobSource {
    let company = "DOU"
    let tier: JobSourceTier = .tier1
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://jobs.dou.ua/vacancies/?category=Swift")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html)
        let links = try document.select("a.vt")

        var jobs: [Job] = []
        var seen: Set<String> = []
        for link in links.array() {
            let title = try link.text()
            guard isIOSJob(title: title) else { continue }
            let href = try link.attr("href")
            guard !href.isEmpty else { continue }
            let jobURL = href.hasPrefix("http") ? href : "https://jobs.dou.ua\(href)"
            guard seen.insert(jobURL).inserted else { continue }
            let companyNode = try? link.parent()?.select("a.company").first()
            let companyName = try companyNode?.text() ?? "Unknown"
            jobs.append(
                Job(
                    title: title,
                    url: jobURL,
                    company: companyName,
                    source: .dou
                )
            )
        }
        return jobs
    }
}
