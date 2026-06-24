import Foundation

protocol JobSource: Sendable {
    var company: String { get }
    func fetchJobs() async throws -> [Job]
}

enum JobSources {
    static func all(http: HTTPClient) -> [any JobSource] {
        [
            DataArtSource(http: http),
            CiklumSource(http: http),
            NixSource(http: http),
            SigmaSource(http: http),
            IntellectsoftSource(http: http),
            IntelliasSource(http: http),
            EleksSource(http: http),
            InfopulseSource(http: http),
            GlobalLogicSource(http: http),
            SoftServeSource(http: http),
            EPAMSource(http: http),
        ]
    }
}
