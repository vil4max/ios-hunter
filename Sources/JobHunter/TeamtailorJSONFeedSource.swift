import Foundation

struct TeamtailorJSONFeedSource: JobSource {
    let company: String
    let tier: JobSourceTier
    private let feedURL: URL
    private let http: HTTPClient

    init(company: String, tier: JobSourceTier, feedURL: URL, http: HTTPClient) {
        self.company = company
        self.tier = tier
        self.feedURL = feedURL
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        var jobs: [Job] = []
        var pageURL: URL? = feedURL

        while let url = pageURL {
            let data = try await http.fetchData(from: url)
            let feed = try JSONDecoder().decode(TeamtailorJSONFeed.self, from: data)

            let pageJobs = feed.items.compactMap { item -> Job? in
                guard isIOSJob(title: item.title) else { return nil }
                return Job(title: item.title, url: item.url, company: company)
            }
            jobs.append(contentsOf: pageJobs)
            pageURL = feed.nextURL
        }

        return jobs
    }
}

private struct TeamtailorJSONFeed: Decodable {
    let items: [TeamtailorJSONItem]
    let nextURL: URL?

    enum CodingKeys: String, CodingKey {
        case items
        case nextURL = "next_url"
    }
}

private struct TeamtailorJSONItem: Decodable {
    let title: String
    let url: String
}
