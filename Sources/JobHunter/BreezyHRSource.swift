import Foundation
import SwiftSoup

struct BreezyHRSource: JobSource {
    let company: String
    let tier: JobSourceTier
    private let portalURL: URL
    private let http: HTTPClient

    init(company: String, tier: JobSourceTier, portalHost: String, http: HTTPClient) {
        self.company = company
        self.tier = tier
        self.portalURL = URL(string: "https://\(portalHost)/")!
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let html = try await http.fetchString(from: portalURL)
        let document = try SwiftSoup.parse(html, portalURL.absoluteString)
        let anchors = try document.select("li.position a[href^=/p/]")
        var jobs: [Job] = []
        var seen = Set<String>()

        for anchor in anchors {
            let href = try anchor.attr("href")
            guard href.hasPrefix("/p/"),
                  let absolute = HTMLHelpers.absoluteURL(href, base: portalURL),
                  seen.insert(absolute).inserted
            else { continue }

            let title = try anchor.select("h2").first()?.text().trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
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
