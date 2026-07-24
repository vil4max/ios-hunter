import Foundation

struct GridDynamicsSource: JobSource {
    let company = "Grid Dynamics"
    let tier: JobSourceTier = .legacy
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://www.griddynamics.com/careers/discover-openings")!
        let html = try await http.fetchString(from: url)
        let vacancies = try parseVacancies(from: html)

        return vacancies.compactMap { vacancy in
            let title = vacancy.title.trimmingCharacters(in: .whitespacesAndNewlines)
            guard isIOSJob(title: title) else { return nil }
            let location = vacancy.locationLabel
            guard isRelevantJobLocation(location) else { return nil }
            let jobURL = "https://www.griddynamics.com/careers/vacancy/\(vacancy.id)"
            return Job(
                title: title,
                url: jobURL,
                company: company,
                details: JobDetails(location: location)
            )
        }
    }

    private func parseVacancies(from html: String) throws -> [GridDynamicsVacancy] {
        let pattern = #"data-vacancies='([^']+)'"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
              let match = regex.firstMatch(in: html, range: NSRange(html.startIndex..., in: html)),
              let jsonRange = Range(match.range(at: 1), in: html)
        else {
            return []
        }

        let json = String(html[jsonRange])
        guard let data = json.data(using: .utf8) else { return [] }
        return try JSONDecoder().decode([GridDynamicsVacancy].self, from: data)
    }
}

private struct GridDynamicsVacancy: Decodable {
    let id: Int
    let title: String
    let relatedLocations: [String]?
    let countryLocations: [GridDynamicsCountryLocation]?

    var locationLabel: String? {
        if let related = relatedLocations?
            .map({ $0.trimmingCharacters(in: .whitespacesAndNewlines) })
            .filter({ !$0.isEmpty }),
           !related.isEmpty
        {
            return related.joined(separator: "; ")
        }
        let countries = (countryLocations ?? []).compactMap { item -> String? in
            let city = item.city?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            let country = item.country?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if !city.isEmpty, !country.isEmpty {
                return "\(city), \(country)"
            }
            if !country.isEmpty {
                return country
            }
            if !city.isEmpty {
                return city
            }
            return nil
        }
        return countries.isEmpty ? nil : countries.joined(separator: "; ")
    }
}

private struct GridDynamicsCountryLocation: Decodable {
    let city: String?
    let country: String?
    let state: String?
}
