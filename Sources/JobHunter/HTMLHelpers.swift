import Foundation
import SwiftSoup

enum HTMLHelpers {
    static func absoluteURL(_ href: String, base: URL) -> String? {
        if href.hasPrefix("http://") || href.hasPrefix("https://") {
            return href
        }
        return URL(string: href, relativeTo: base)?.absoluteString
    }

    static func parseVacancyItems(
        html: String,
        baseURL: URL,
        itemSelector: String,
        titleSelector: String,
        linkAttribute: String = "href",
        company: String
    ) throws -> [Job] {
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let items = try document.select(itemSelector)
        var jobs: [Job] = []

        for item in items {
            let href = try item.attr(linkAttribute)
            guard !href.isEmpty,
                  let url = absoluteURL(href, base: baseURL)
            else { continue }

            let title = try item.select(titleSelector).first()?.text().trimmingCharacters(in: .whitespacesAndNewlines)
                ?? item.text().trimmingCharacters(in: .whitespacesAndNewlines)
            guard !title.isEmpty else { continue }
            jobs.append(Job(title: title, url: url, company: company))
        }

        return jobs
    }
}
