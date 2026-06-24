import Foundation

struct CiklumSource: JobSource {
    let company = "Ciklum"
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let finder = "findReqs;siteNumber=CX_1001,keyword=ios,limit=50,offset=0"
        var components = URLComponents(string: "https://ialmme.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions")!
        components.queryItems = [
            URLQueryItem(name: "onlyData", value: "true"),
            URLQueryItem(name: "expand", value: "requisitionList"),
            URLQueryItem(name: "finder", value: finder),
        ]

        guard let url = components.url else { return [] }

        let data = try await http.fetchData(from: url)
        let response = try JSONDecoder().decode(CiklumResponse.self, from: data)
        let requisitions = response.items.first?.requisitionList ?? []

        return requisitions.compactMap { item in
            guard isIOSJob(title: item.title) else { return nil }
            let jobURL = "https://explore-jobs.ciklum.com/en/sites/ciklum-career/job/\(item.id)"
            return Job(title: item.title, url: jobURL, company: company)
        }
    }
}

private struct CiklumResponse: Decodable {
    let items: [CiklumSearchItem]
}

private struct CiklumSearchItem: Decodable {
    let requisitionList: [CiklumRequisition]?
}

private struct CiklumRequisition: Decodable {
    let id: String
    let title: String

    enum CodingKeys: String, CodingKey {
        case id = "Id"
        case title = "Title"
    }
}
