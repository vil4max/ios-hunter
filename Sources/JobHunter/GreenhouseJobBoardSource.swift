import Foundation

struct GreenhouseJobBoardSource: JobSource {
    let company: String
    let tier: JobSourceTier
    private let boardSlug: String
    private let http: HTTPClient

    init(company: String, tier: JobSourceTier, boardSlug: String, http: HTTPClient) {
        self.company = company
        self.tier = tier
        self.boardSlug = boardSlug
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://boards-api.greenhouse.io/v1/boards/\(boardSlug)/jobs?content=true")!
        let data = try await http.fetchData(from: url)
        let response = try JSONDecoder().decode(GreenhouseJobBoardResponse.self, from: data)

        return response.jobs.compactMap { item in
            guard isIOSJob(title: item.title) else { return nil }
            return Job(title: item.title, url: item.absoluteURL, company: company)
        }
    }
}

private struct GreenhouseJobBoardResponse: Decodable {
    let jobs: [GreenhouseJobBoardJob]
}

private struct GreenhouseJobBoardJob: Decodable {
    let title: String
    let absoluteURL: String

    enum CodingKeys: String, CodingKey {
        case title
        case absoluteURL = "absolute_url"
    }
}
