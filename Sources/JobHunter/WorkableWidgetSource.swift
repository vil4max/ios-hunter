import Foundation

struct WorkableWidgetSource: JobSource {
    let company: String
    let tier: JobSourceTier
    private let accountSlug: String
    private let http: HTTPClient

    init(company: String, tier: JobSourceTier, accountSlug: String, http: HTTPClient) {
        self.company = company
        self.tier = tier
        self.accountSlug = accountSlug
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://apply.workable.com/api/v1/widget/accounts/\(accountSlug)")!
        let data = try await http.fetchData(from: url)
        let response = try JSONDecoder().decode(WorkableWidgetResponse.self, from: data)

        var seen = Set<String>()
        return response.jobs.compactMap { item in
            guard isIOSJob(title: item.title),
                  seen.insert(item.url).inserted
            else { return nil }
            return Job(title: item.title, url: item.url, company: company)
        }
    }
}

private struct WorkableWidgetResponse: Decodable {
    let jobs: [WorkableWidgetJob]
}

private struct WorkableWidgetJob: Decodable {
    let title: String
    let url: String
}
