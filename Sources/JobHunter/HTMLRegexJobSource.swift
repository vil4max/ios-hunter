import Foundation

struct HTMLRegexJobSource: JobSource {
    let company: String
    let tier: JobSourceTier
    private let listURL: URL
    private let baseURL: URL
    private let pattern: String
    private let urlGroup: Int
    private let titleGroup: Int?
    private let useListURLAsJobURL: Bool
    private let http: HTTPClient

    init(
        company: String,
        tier: JobSourceTier,
        listURL: URL,
        baseURL: URL,
        pattern: String,
        urlGroup: Int = 1,
        titleGroup: Int? = nil,
        useListURLAsJobURL: Bool = false,
        http: HTTPClient
    ) {
        self.company = company
        self.tier = tier
        self.listURL = listURL
        self.baseURL = baseURL
        self.pattern = pattern
        self.urlGroup = urlGroup
        self.titleGroup = titleGroup
        self.useListURLAsJobURL = useListURLAsJobURL
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        let html = try await http.fetchString(from: listURL)
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]) else {
            return []
        }

        let range = NSRange(html.startIndex..., in: html)
        var seen = Set<String>()
        var jobs: [Job] = []

        regex.enumerateMatches(in: html, options: [], range: range) { match, _, _ in
            guard let match else { return }

            let title: String
            if let titleGroup,
               titleGroup < match.numberOfRanges,
               match.range(at: titleGroup).location != NSNotFound,
               let titleRange = Range(match.range(at: titleGroup), in: html) {
                title = String(html[titleRange]).trimmingCharacters(in: .whitespacesAndNewlines)
            } else if urlGroup < match.numberOfRanges,
                      match.range(at: urlGroup).location != NSNotFound,
                      let urlRange = Range(match.range(at: urlGroup), in: html) {
                title = titleFromURL(String(html[urlRange]))
            } else {
                return
            }

            guard !title.isEmpty else { return }

            let jobURL: String
            if useListURLAsJobURL {
                jobURL = listURL.absoluteString
            } else {
                guard urlGroup < match.numberOfRanges,
                      match.range(at: urlGroup).location != NSNotFound,
                      let urlRange = Range(match.range(at: urlGroup), in: html)
                else { return }
                jobURL = absoluteURL(String(html[urlRange]))
            }

            let dedupeKey = useListURLAsJobURL ? title : jobURL
            guard seen.insert(dedupeKey).inserted else { return }
            guard isIOSJob(title: title) else { return }
            jobs.append(Job(title: title, url: jobURL, company: company))
        }

        return jobs
    }

    private func absoluteURL(_ href: String) -> String {
        let trimmed = href.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.hasPrefix("http://") || trimmed.hasPrefix("https://") {
            return trimmed
        }
        if trimmed.hasPrefix("/") {
            return baseURL.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/")) + trimmed
        }
        return URL(string: trimmed, relativeTo: baseURL)?.absoluteString ?? trimmed
    }

    private func titleFromURL(_ value: String) -> String {
        let path = value.split(separator: "?").first.map(String.init) ?? value
        return path
            .split(separator: "/")
            .filter { !$0.isEmpty }
            .last?
            .replacingOccurrences(of: "-", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? value
    }
}
