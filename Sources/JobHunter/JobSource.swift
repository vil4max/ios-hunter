import Foundation

protocol JobSource: Sendable {
    var company: String { get }
    var tier: JobSourceTier { get }
    func fetchJobs() async throws -> [Job]
}

enum JobSources {
    static func all(http: HTTPClient) -> [any JobSource] {
        [
            LeobitSource(http: http),
            AndersenSource(http: http),
            NixSource(http: http),
            SPDSource(http: http),
            DevProSource(http: http),
            IntelliasSource(http: http),
            MWDNSource(http: http),
            OnixSource(http: http),
            QAreaSource(http: http),
            ExoftSource(http: http),
            SoftjournSource(http: http),
            EleksSource(http: http),
            AgiliwaySource(http: http),
            InnovecsSource(http: http),
            TeamtailorJSONFeedSource(
                company: "Avenga",
                tier: .tier3,
                feedURL: URL(string: "https://career.avenga.com/jobs.json")!,
                http: http
            ),
            DevlightSource(http: http),
            CiklumSource(http: http),
            SigmaSource(http: http),
            InfopulseSource(http: http),
            AshbyJobBoardSource(company: "Genesis", tier: .product, boardSlug: "Genesis", http: http),
            AshbyJobBoardSource(company: "SKELAR", tier: .product, boardSlug: "SKELAR", http: http),
            MacPawSource(http: http),
            AshbyJobBoardSource(company: "Ajax Systems", tier: .product, boardSlug: "Ajax", http: http),
            WorkableWidgetSource(company: "BetterMe", tier: .product, accountSlug: "betterme", http: http),
            AshbyJobBoardSource(company: "Grammarly", tier: .product, boardSlug: "Superhuman", http: http),
            AshbyJobBoardSource(company: "Solvd", tier: .tier3, boardSlug: "Solvd", http: http),
            DataArtSource(http: http),
            IntellectsoftSource(http: http),
            GlobalLogicSource(http: http),
            SoftServeSource(http: http),
            EPAMSource(http: http),
        ]
    }
}
