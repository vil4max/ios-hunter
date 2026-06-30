import Foundation

struct GridDynamicsSource: JobSource {
    let company = "Grid Dynamics"
    let tier: JobSourceTier = .legacy
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://www.griddynamics.com/careers/discover-openings")!
        let html = try await http.fetchString(from: url)
        let vacancies = try parseVacancies(from: html)

        return vacancies.compactMap { vacancy in
            guard isIOSJob(title: vacancy.title) else { return nil }
            let jobURL = "https://www.griddynamics.com/careers/vacancy/\(vacancy.id)"
            return Job(title: vacancy.title.trimmingCharacters(in: .whitespacesAndNewlines), url: jobURL, company: company)
        }
    }

    private func parseVacancies(from html: String) throws -> [GridDynamicsVacancy] {
        let pattern = #"data-vacancies='([^']+)'"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
              let match = regex.firstMatch(in: html, range: NSRange(html.startIndex..., in: html)),
              let jsonRange = Range(match.range(at: 1), in: html)
        else {
            return []
        }

        let json = String(html[jsonRange])
        guard let data = json.data(using: .utf8) else { return [] }
        return try JSONDecoder().decode([GridDynamicsVacancy].self, from: data)
    }
}

private struct GridDynamicsVacancy: Decodable {
    let id: Int
    let title: String
}
