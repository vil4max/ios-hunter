import Foundation

struct AndersenSource: JobSource {
    let company = "Andersen"
    let tier: JobSourceTier = .tier1
    private let http: HTTPClient

    private let apiURL = URL(string: "https://asite-api.andersenlab.com/api/integration/recruitment/vacancies")!

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let data = try await http.fetchData(
            from: apiURL,
            headers: [
                "Accept-Language": "en",
                "Accept": "application/json",
            ]
        )
        let vacancies = try JSONDecoder().decode([AndersenVacancy].self, from: data)

        return vacancies.compactMap { vacancy in
            guard vacancy.matchesIOS else { return nil }
            let jobURL = "https://people.andersenlab.com/vacancy/\(vacancy.vacancyID)"
            return Job(title: vacancy.name, url: jobURL, company: company)
        }
    }
}

private struct AndersenVacancy: Decodable {
    let vacancyID: Int
    let name: String
    let technologies: [String]?

    enum CodingKeys: String, CodingKey {
        case vacancyID = "vacancy_id"
        case name
        case technologies
    }

    var matchesIOS: Bool {
        if isIOSJob(title: name) {
            return true
        }
        return technologies?.contains(where: { isIOSJob(title: $0) }) == true
    }
}
