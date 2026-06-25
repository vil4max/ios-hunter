import Foundation

struct IntellectsoftSource: JobSource {
    let company = "Intellectsoft"
    let tier: JobSourceTier = .legacy
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://apply.workable.com/api/v1/widget/accounts/intellectsoft")!
        let data = try await http.fetchData(from: url)
        let response = try JSONDecoder().decode(WorkableResponse.self, from: data)

        var seen = Set<String>()
        return response.jobs.compactMap { item in
            guard isIOSJob(title: item.title),
                  seen.insert(item.url).inserted
            else { return nil }
            return Job(title: item.title, url: item.url, company: company)
        }
    }
}

private struct WorkableResponse: Decodable {
    let jobs: [WorkableJob]
}

private struct WorkableJob: Decodable {
    let title: String
    let url: String
}
