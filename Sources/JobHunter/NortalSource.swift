import Foundation

struct NortalSource: JobSource {
    let company = "Nortal"
    let tier: JobSourceTier = .tier2
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://nortal.career.page/api/jobs?location=Ukraine")!
        let data = try await http.fetchData(from: url)
        let response = try JSONDecoder().decode(NortalJobsResponse.self, from: data)

        return response.jobs.compactMap { item in
            guard isIOSJob(title: item.data.title) else { return nil }
            return Job(title: item.data.title, url: item.data.applyURL, company: company)
        }
    }
}

private struct NortalJobsResponse: Decodable {
    let jobs: [NortalJobItem]
}

private struct NortalJobItem: Decodable {
    let data: NortalJobData
}

private struct NortalJobData: Decodable {
    let title: String
    let applyURL: String

    enum CodingKeys: String, CodingKey {
        case title
        case applyURL = "apply_url"
    }
}
