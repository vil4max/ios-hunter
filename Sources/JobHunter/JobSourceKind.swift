import Foundation

enum JobSourceKind: String, Codable, Sendable {
    case linkedin
    case dou
    case djinni
    case company
}

enum RemoteType: String, Codable, Sendable {
    case remote
    case hybrid
    case onsite
    case unknown
}
