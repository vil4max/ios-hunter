import Foundation

struct JobDetails: Sendable {
    var location: String?
    var remote: RemoteType?
    var published: Date?
    var source: JobSourceKind
    var description: String?

    init(
        location: String? = nil,
        remote: RemoteType? = nil,
        published: Date? = nil,
        source: JobSourceKind = .company,
        description: String? = nil
    ) {
        self.location = location
        self.remote = remote
        self.published = published
        self.source = source
        self.description = description
    }
}

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
        details: JobDetails = JobDetails()
    ) {
        self.title = title
        self.url = url
        self.company = company
        self.location = details.location
        self.remote = details.remote
        self.published = details.published
        self.source = details.source
        self.description = details.description
    }

    var hash: String {
        JobHash.compute(company: company, title: title, location: location)
    }
}
