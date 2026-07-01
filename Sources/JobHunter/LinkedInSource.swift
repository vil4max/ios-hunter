import Foundation

struct LinkedInSource: JobSource {
    let company = "LinkedIn"
    let tier: JobSourceTier = .tier2
    private let http: HTTPClient

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        _ = http
        fputs("[LinkedIn] stub source — not implemented yet\n", stderr)
        return []
    }
}
