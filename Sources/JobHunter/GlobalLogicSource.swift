import Foundation
import SwiftSoup

struct GlobalLogicSource: JobSource {
    let company = "GlobalLogic"
    let tier: JobSourceTier = .legacy
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://www.globallogic.com/")!
        let url = URL(string: "https://www.globallogic.com/ua/career-search-page/?keywords=ios")!
        let html = try await http.fetchString(from: url)
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let links = try document.select("a.job_box[href*=/ua/careers/]")
        var jobs: [Job] = []
        var seen = Set<String>()

        for link in links {
            let href = try link.attr("href")
            guard href.contains("-irc"),
                  let absolute = HTMLHelpers.absoluteURL(href, base: baseURL),
                  seen.insert(absolute).inserted
            else { continue }

            let title = try link.select("h4").first()?.text().trimmingCharacters(in: .whitespacesAndNewlines)
                ?? link.text().trimmingCharacters(in: .whitespacesAndNewlines)
            let cleaned = title.replacingOccurrences(of: #"\s+IRC\d+\s*$"#, with: "", options: .regularExpression)
            guard !cleaned.isEmpty, isIOSJob(title: cleaned) else { continue }
            jobs.append(Job(title: cleaned, url: absolute, company: company))
        }

        if !jobs.isEmpty {
            return jobs
        }

        return try parseFallbackLinks(html: html)
    }

    private func parseFallbackLinks(html: String) throws -> [Job] {
        let pattern = #"https://www\.globallogic\.com/ua/careers/[a-z0-9-]+-irc\d+/?"#
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var seen = Set<String>()
        var jobs: [Job] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match, let urlRange = Range(match.range, in: html) else { return }
            let jobURL = String(html[urlRange])
            guard seen.insert(jobURL).inserted else { return }

            let slug = jobURL.split(separator: "/").last ?? ""
            let title = slug
                .replacingOccurrences(of: "-", with: " ")
                .replacingOccurrences(of: #"irc\d+"#, with: "", options: .regularExpression)
                .trimmingCharacters(in: .whitespacesAndNewlines)

            guard isIOSJob(title: title) else { return }
            jobs.append(Job(title: title, url: jobURL, company: company))
        }

        return jobs
    }
}
