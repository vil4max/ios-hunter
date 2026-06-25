import Foundation

struct AshbyJobBoardSource: JobSource {
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
        let url = URL(string: "https://api.ashbyhq.com/posting-api/job-board/\(boardSlug)")!
        let data = try await http.fetchData(from: url)
        let response = try JSONDecoder().decode(AshbyJobBoardResponse.self, from: data)

        return response.jobs.compactMap { item in
            guard isIOSJob(title: item.title) else { return nil }
            return Job(title: item.title, url: item.jobURL, company: company)
        }
    }
}

private struct AshbyJobBoardResponse: Decodable {
    let jobs: [AshbyJobBoardJob]
}

private struct AshbyJobBoardJob: Decodable {
    let title: String
    let jobURL: String

    enum CodingKeys: String, CodingKey {
        case title
        case jobURL = "jobUrl"
    }
}
