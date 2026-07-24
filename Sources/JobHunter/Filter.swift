import Foundation

func isIOSJob(title: String) -> Bool {
    let denyPattern =
        #"(?i)(?<![A-Za-z0-9])(qa|sdet|tpm|kmm|kotlin\s+multiplatform|quality\s+assurance|test(?:ing)?\s+(?:automation|engineer|developer)|automation\s+(?:qa|engineer|tester)|manual\s+qa|mobile\s+automation)(?![A-Za-z0-9])"#
    if title.range(of: denyPattern, options: .regularExpression) != nil {
        return false
    }
    let pattern =
        #"(?i)(?<![A-Za-z0-9])(ios|swift|swiftui|uikit|objective[\s\-]?c|objc|obj[\s\-]?c|xcode|iphone|ipad|tvos|watchos|visionos|cocoa(?:pods|touch)?)(?![A-Za-z0-9])"#
    return title.range(of: pattern, options: .regularExpression) != nil
}

func isRelevantJobLocation(_ location: String?) -> Bool {
    let text = (location ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    if text.isEmpty {
        return true
    }
    let lowered = text.lowercased()
    if lowered.range(of: #"\b(remote|remotely|worldwide|anywhere|emea|europe|eu)\b"#, options: .regularExpression) != nil {
        return true
    }
    let denyPattern =
        #"(?i)\b(argentina|buenos\s+aires|brazil|mexico|chile|colombia|peru|india|bengaluru|bangalore|hyderabad|pune|chennai|philippines|vietnam|china)\b"#
    return lowered.range(of: denyPattern, options: .regularExpression) == nil
}
