import Foundation

struct InnovecsSource: JobSource {
    let company = "Innovecs"
    let tier: JobSourceTier = .tier3
    private let greenhouse: GreenhouseJobBoardSource

    init(http: HTTPClient) {
        self.greenhouse = GreenhouseJobBoardSource(
            company: "Innovecs",
            tier: .tier3,
            boardSlug: "innovecs",
            http: http
        )
    }

    func fetchJobs() async throws -> [Job] {
        try await greenhouse.fetchJobs()
    }
}
