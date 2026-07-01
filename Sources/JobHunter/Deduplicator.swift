import Foundation

enum Deduplicator {
    static func unique(jobs: [Job]) -> (jobs: [Job], removed: Int) {
        var seen: Set<String> = []
        var unique: [Job] = []
        var removed = 0
        for job in jobs {
            if seen.contains(job.hash) {
                removed += 1
                continue
            }
            seen.insert(job.hash)
            unique.append(job)
        }
        return (unique, removed)
    }
}
