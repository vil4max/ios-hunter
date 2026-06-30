import Foundation

struct YalantisSource: JobSource {
    let company = "Yalantis"
    let tier: JobSourceTier = .tier2
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://yalantis.ua/wp-json/wp/v2/vacancies?per_page=100")!
        let data = try await http.fetchData(from: url)
        let items = try JSONDecoder().decode([WordPressREST.VacancyItem].self, from: data)

        return items.compactMap { item in
            let title = item.plainTitle
            guard isIOSJob(title: title) else { return nil }
            return Job(title: title, url: item.link, company: company)
        }
    }
}
