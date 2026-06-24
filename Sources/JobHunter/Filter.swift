import Foundation

func isIOSJob(title: String) -> Bool {
    let lowered = title.lowercased()
    guard lowered.contains("ios") || lowered.contains("swift") else {
        return false
    }
    return true
}

func filterIOSJobs(_ jobs: [Job]) -> [Job] {
    jobs.filter { isIOSJob(title: $0.title) }
}
