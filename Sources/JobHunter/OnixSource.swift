import Foundation

struct OnixSource: JobSource {
    let company = "Onix Systems"
    let tier: JobSourceTier = .tier2
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let url = URL(string: "https://onix-systems.com/careers")!
        let html = try await http.fetchString(from: url)
        guard let data = NextDataHelpers.jsonData(from: html) else { return [] }

        let page = try JSONDecoder().decode(OnixCareersPage.self, from: data)

        return page.props.pageProps.careerList.compactMap { entry in
            let attributes = entry.attributes
            guard isIOSJob(title: attributes.name) else { return nil }
            let jobURL = attributes.canonical ?? "https://onix-systems.com/careers/\(attributes.url)"
            return Job(title: attributes.name, url: jobURL, company: company)
        }
    }
}

private struct OnixCareersPage: Decodable {
    let props: Props

    struct Props: Decodable {
        let pageProps: PageProps
    }

    struct PageProps: Decodable {
        let careerList: [CareerEntry]
    }

    struct CareerEntry: Decodable {
        let attributes: Attributes
    }

    struct Attributes: Decodable {
        let name: String
        let url: String
        let canonical: String?
    }
}
