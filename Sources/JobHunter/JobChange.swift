import Foundation

enum JobChangeKind: String, Sendable {
    case new
    case updated
    case closed
    case reopened
    case unchanged
}

struct JobChange: Sendable {
    let jobID: String
    let kind: JobChangeKind
    let diff: String?
    let summary: String?
}
