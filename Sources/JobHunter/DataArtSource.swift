import Foundation

struct DataArtSource: JobSource {
    let company = "DataArt"
    let tier: JobSourceTier = .legacy
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://www.dataart.team/dataart-team/api/vacancies/filter-fields-page?skills=771")!
        let data = try await http.fetchData(from: url)
        let response = try JSONDecoder().decode(DataArtResponse.self, from: data)

        return response.vacancies.items.compactMap { item in
            guard isIOSJob(title: item.title) else { return nil }
            let jobURL = "https://www.dataart.team/vacancies/\(item.slug)"
            return Job(title: item.title, url: jobURL, company: company)
        }
    }
}

private struct DataArtResponse: Decodable {
    let vacancies: DataArtVacancies
}

private struct DataArtVacancies: Decodable {
    let items: [DataArtVacancy]
}

private struct DataArtVacancy: Decodable {
    let title: String
    let slug: String
}
