import Foundation

struct RBISource: JobSource {
    let company = "RBI Retail Innovation"
    let tier: JobSourceTier = .product
    private let http: HTTPClient

    private let baseURL = URL(string: "https://www.rbi-ri.com.ua/")!
    private let listURL = URL(string: "https://www.rbi-ri.com.ua/career")!
    private let sitemapURL = URL(string: "https://www.rbi-ri.com.ua/sitemap.xml")!

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let sitemapURLs = try await fetchCareerURLsFromSitemap()
        let listPageURLs = try await fetchCareerURLsFromListPage()
        let vacancyURLs = Set(sitemapURLs + listPageURLs)

        var jobs: [Job] = []
        for url in vacancyURLs.sorted() {
            guard let job = try await fetchJob(from: url) else { continue }
            jobs.append(job)
        }
        return jobs
    }

    private func fetchCareerURLsFromSitemap() async throws -> [String] {
        let xml = try await http.fetchString(from: sitemapURL)
        let pattern = #"<loc>(https://www\.rbi-ri\.com\.ua/career/[a-z0-9-]+)</loc>"#
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(xml.startIndex..., in: xml)
        var urls: [String] = []

        regex.enumerateMatches(in: xml, options: [], range: range) { match, _, _ in
            guard let match, let urlRange = Range(match.range(at: 1), in: xml) else { return }
            urls.append(String(xml[urlRange]))
        }

        return urls
    }

    private func fetchCareerURLsFromListPage() async throws -> [String] {
        let html = try await http.fetchString(from: listURL)
        let pattern = #"https?://(?:www\.)?rbi-ri\.com\.ua/career/([a-z0-9-]+)"#
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var urls: [String] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match, let urlRange = Range(match.range, in: html) else { return }
            urls.append(String(html[urlRange]))
        }

        return urls
    }

    private func fetchJob(from urlString: String) async throws -> Job? {
        guard let url = URL(string: urlString) else { return nil }
        let html = try await http.fetchString(from: url)
        guard let title = extractTitle(from: html), isIOSJob(title: title) else { return nil }
        return Job(title: title, url: urlString, company: company)
    }

    private func extractTitle(from html: String) -> String? {
        let patterns = [
            #"<meta property="og:title" content="([^"]+)"\s*/?>"#,
            #"<title>([^<]+)</title>"#,
        ]

        for pattern in patterns {
            guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
                continue
            }
            let range = NSRange(html.startIndex..., in: html)
            guard let match = regex.firstMatch(in: html, options: [], range: range),
                  let titleRange = Range(match.range(at: 1), in: html)
            else { continue }

            let rawTitle = String(html[titleRange]).trimmingCharacters(in: .whitespacesAndNewlines)
            let cleaned = cleanTitle(rawTitle)
            if !cleaned.isEmpty {
                return cleaned
            }
        }

        return nil
    }

    private func cleanTitle(_ title: String) -> String {
        title
            .replacingOccurrences(of: #"^Vacancy\s+"#, with: "", options: .regularExpression)
            .replacingOccurrences(of: #"\s+—\s+RBI Retail Innovation\s*$"#, with: "", options: .regularExpression)
            .replacingOccurrences(of: #"&#039;"#, with: "'")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
