import Foundation

enum JobSourceTier: Int, Sendable, Comparable {
    case tier1 = 1
    case tier2 = 2
    case tier3 = 3
    case product = 4
    case legacy = 5

    static func < (lhs: JobSourceTier, rhs: JobSourceTier) -> Bool {
        lhs.rawValue < rhs.rawValue
    }
}
