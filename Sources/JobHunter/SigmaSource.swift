import Foundation
import SwiftSoup

struct SigmaSource: JobSource {
    let company = "Sigma Software"
    private let http: HTTPClient

    private let ajaxURL = URL(string: "https://career.sigma.software/wp-admin/admin-ajax.php")!

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://career.sigma.software/")!
        var jobs: [Job] = []
        var seen = Set<String>()
        var page = 1
        var hasMore = true

        while hasMore {
            let action = page == 1 ? "filter_vacancies_v2" : "filter_vacancies_v2_loadmore"
            var fields = filterFields(action: action)
            if page > 1 {
                fields["page"] = String(page - 1)
            }

            let response = try await fetchVacancyPage(fields: fields)
            guard response.success, let data = response.data else { break }

            let pageJobs = try parseJobs(html: data.html, baseURL: baseURL, seen: &seen)
            jobs.append(contentsOf: pageJobs)

            hasMore = data.hasMore
            page += 1
        }

        return jobs
    }

    private func filterFields(action: String) -> [String: String] {
        [
            "action": action,
            "keyword": "",
            "direction": "[\"engineering\"]",
            "direction_type": "parent",
            "locations": "[]",
            "seniority": "[]",
            "workplace_type": "[]",
        ]
    }

    private func fetchVacancyPage(fields: [String: String]) async throws -> SigmaVacancyResponse {
        let data = try await http.postForm(to: ajaxURL, fields: fields)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(SigmaVacancyResponse.self, from: data)
    }

    private func parseJobs(html: String, baseURL: URL, seen: inout Set<String>) throws -> [Job] {
        let document = try SwiftSoup.parse(html, baseURL.absoluteString)
        let cards = try document.select("a.vacancy-card-new")
        var jobs: [Job] = []

        for card in cards {
            let href = try card.attr("href")
            guard let absolute = HTMLHelpers.absoluteURL(href, base: baseURL),
                  seen.insert(absolute).inserted
            else { continue }

            let title = try card.select("h3.vacancy-card-new__title").first()?
                .text()
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            let technologies = try card.select("div.vacancy-card-new__technologies span").first()?
                .text()
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

            guard !title.isEmpty, isIOSJob(title: title) || isIOSJob(title: technologies) else { continue }
            jobs.append(Job(title: title, url: absolute, company: company))
        }

        return jobs
    }
}

private struct SigmaVacancyResponse: Decodable {
    let success: Bool
    let data: SigmaVacancyData?
}

private struct SigmaVacancyData: Decodable {
    let html: String
    let hasMore: Bool
}
