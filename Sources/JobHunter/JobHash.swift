import CryptoKit
import Foundation

enum JobHash {
    static func compute(company: String, title: String, location: String?) -> String {
        let raw = [normalize(company), normalize(title), normalize(location ?? "")].joined(separator: "|")
        let digest = SHA256.hash(data: Data(raw.utf8))
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    private static func normalize(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}
