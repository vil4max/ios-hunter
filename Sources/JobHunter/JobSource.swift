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
                company: "Levi9",
                tier: .tier2,
                feedURL: URL(string: "https://jobs.ua.levi9.com/jobs.json")!,
                http: http
            ),
            TeamtailorJSONFeedSource(
                company: "Avenga",
                tier: .tier3,
                feedURL: URL(string: "https://career.avenga.com/jobs.json")!,
                http: http
            ),
            HTMLRegexJobSource(
                company: "CHI Software",
                tier: .tier2,
                listURL: URL(string: "https://chisw.com/careers/vacancies/")!,
                baseURL: URL(string: "https://chisw.com/")!,
                pattern: #"https://chisw\.com/vacancies/([a-z0-9-]+)/"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "JetSoftPro",
                tier: .tier3,
                listURL: URL(string: "https://career.jetsoftpro.com/vacancies/")!,
                baseURL: URL(string: "https://career.jetsoftpro.com/")!,
                pattern: #"https://career\.jetsoftpro\.com/vacancies/([a-z0-9-]+)/"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "Sombra",
                tier: .tier3,
                listURL: URL(string: "https://sombrainc.com/careers")!,
                baseURL: URL(string: "https://sombrainc.com/")!,
                pattern: #"https://sombrainc\.com/careers/(?!page|feed)([a-z0-9-]+(?:-[a-z0-9-]+)*)"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "Vakoms",
                tier: .tier3,
                listURL: URL(string: "https://vakoms.com/careers")!,
                baseURL: URL(string: "https://vakoms.com/")!,
                pattern: #"/careers/([a-z0-9-]+(?:-[a-z0-9-]+)+)"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "Binary Studio",
                tier: .tier2,
                listURL: URL(string: "https://binary-studio.com/careers/")!,
                baseURL: URL(string: "https://binary-studio.com/")!,
                pattern: #"https://binary-studio\.com/careers/([a-z0-9-]+)/"#,
                http: http
            ),
            WorkableWidgetSource(company: "KindGeek", tier: .tier3, accountSlug: "kindgeek", http: http),
            HTMLRegexJobSource(
                company: "Inoxoft",
                tier: .tier3,
                listURL: URL(string: "https://inoxoft.com/vacancies/")!,
                baseURL: URL(string: "https://inoxoft.com/")!,
                pattern: #"https://inoxoft\.com/vacancies/([a-z0-9-]+)/"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "Otakoyi",
                tier: .tier3,
                listURL: URL(string: "https://otakoyi.software/careers/")!,
                baseURL: URL(string: "https://otakoyi.software/")!,
                pattern: #"/careers/([a-z0-9-]+(?:-[a-z0-9-]+)+)"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "AltexSoft",
                tier: .legacy,
                listURL: URL(string: "https://www.altexsoft.com/careers/")!,
                baseURL: URL(string: "https://www.altexsoft.com/")!,
                pattern: #"https://www\.altexsoft\.com/vacancy/([a-z0-9-]+)/"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "Mind Studios",
                tier: .product,
                listURL: URL(string: "https://themindstudios.com/careers/")!,
                baseURL: URL(string: "https://themindstudios.com/")!,
                pattern: #"https://themindstudios.com/careers/([a-z0-9-]+)/"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "Computools",
                tier: .tier3,
                listURL: URL(string: "https://computools.com/careers/")!,
                baseURL: URL(string: "https://computools.com/")!,
                pattern: #"https://computools\.com/career/([a-z0-9-]+)/"#,
                http: http
            ),
            HTMLRegexJobSource(
                company: "Zfort",
                tier: .tier3,
                listURL: URL(string: "https://www.zfort.com/company/careers")!,
                baseURL: URL(string: "https://www.zfort.com/")!,
                pattern: #"<h3 class=\"chess-item-title\">([^<]+)</h3>"#,
                titleGroup: 1,
                useListURLAsJobURL: true,
                http: http
            ),
            NortalSource(http: http),
            WorkableWidgetSource(company: "Lohika", tier: .legacy, accountSlug: "lohika", http: http),
            WorkableWidgetSource(company: "Apriorit", tier: .tier3, accountSlug: "apriorit", http: http),
            WorkableWidgetSource(company: "Geniusee", tier: .product, accountSlug: "geniusee", http: http),
            YalantisSource(http: http),
            HTMLRegexJobSource(
                company: "Inverita",
                tier: .tier3,
                listURL: URL(string: "https://inveritasoft.com/vacancies")!,
                baseURL: URL(string: "https://inveritasoft.com/")!,
                pattern: #"<h3 class=\"font-25\">\s*([^<]+?)\s*</h3>[\s\S]*?href=\"(https://inveritasoft\.com/article-[^\"]+)\""#,
                urlGroup: 2,
                titleGroup: 1,
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
            AshbyJobBoardSource(company: "KissMyApps", tier: .product, boardSlug: "kissmyapps", http: http),
            DataArtSource(http: http),
            IntellectsoftSource(http: http),
            GlobalLogicSource(http: http),
            GridDynamicsSource(http: http),
            SoftServeSource(http: http),
            EPAMSource(http: http),
            RBISource(http: http),
        ]
    }
}
