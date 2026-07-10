import Foundation

func isIOSJob(title: String) -> Bool {
    let lowered = title.lowercased()
    guard lowered.contains("ios") || lowered.contains("swift") else {
        return false
    }
    return true
}
