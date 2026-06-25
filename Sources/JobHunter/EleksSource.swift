import Foundation

struct EleksSource: JobSource {
    let company = "Eleks"
    let tier: JobSourceTier = .tier1
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let baseURL = URL(string: "https://careers.eleks.com/")!
        let url = URL(string: "https://careers.eleks.com/vacancies/")!
        let html = try await http.fetchString(from: url)

        return try HTMLHelpers.parseVacancyItems(
            html: html,
            baseURL: baseURL,
            itemSelector: "a.vacancy-item",
            titleSelector: ".vacancy-item__title",
            company: company
        ).filter { isIOSJob(title: $0.title) }
    }
}
