import Foundation

struct Job: Hashable, Sendable {
    let title: String
    let url: String
    let company: String
    let location: String?
    let remote: RemoteType?
    let published: Date?
    let source: JobSourceKind
    let description: String?

    init(
        title: String,
        url: String,
        company: String,
        location: String? = nil,
        remote: RemoteType? = nil,
        published: Date? = nil,
        source: JobSourceKind = .company,
        description: String? = nil
    ) {
        self.title = title
        self.url = url
        self.company = company
        self.location = location
        self.remote = remote
        self.published = published
        self.source = source
        self.description = description
    }

    var hash: String {
        JobHash.compute(company: company, title: title, location: location)
    }
}
