import Foundation
import SQLite3

final class JobRepository: Sendable {
    private nonisolated(unsafe) let db: OpaquePointer?

    init(path: String) throws {
        let directory = (path as NSString).deletingLastPathComponent
        if !directory.isEmpty {
            try FileManager.default.createDirectory(atPath: directory, withIntermediateDirectories: true)
        }

        var database: OpaquePointer?
        if sqlite3_open(path, &database) != SQLITE_OK {
            throw RepositoryError.openFailed(String(cString: sqlite3_errmsg(database)))
        }
        db = database
        try migrate()
    }

    deinit {
        sqlite3_close(db)
    }

    private func migrate() throws {
        let sql = """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            remote TEXT,
            url TEXT NOT NULL,
            source TEXT NOT NULL,
            published_at TEXT,
            updated_at TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            description TEXT,
            hash TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            diff TEXT
        );
        CREATE TABLE IF NOT EXISTS job_sources (
            job_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            seen_at TEXT NOT NULL,
            PRIMARY KEY (job_id, source, source_url)
        );
        CREATE TABLE IF NOT EXISTS seen_urls (
            url TEXT PRIMARY KEY NOT NULL
        );
        """
        if sqlite3_exec(db, sql, nil, nil, nil) != SQLITE_OK {
            throw RepositoryError.execFailed(String(cString: sqlite3_errmsg(db)))
        }
        try importLegacySeenURLsIfNeeded()
    }

    private func importLegacySeenURLsIfNeeded() throws {
        let legacyPaths = ["data/jobs.sqlite", "database/jobs.db"]
        for legacyPath in legacyPaths {
            guard FileManager.default.fileExists(atPath: legacyPath) else { continue }
            let count = scalarInt("SELECT COUNT(*) FROM seen_urls") ?? 0
            guard count == 0 else { return }

            var legacyDB: OpaquePointer?
            guard sqlite3_open(legacyPath, &legacyDB) == SQLITE_OK else { continue }
            defer { sqlite3_close(legacyDB) }

            let sql = "SELECT url FROM seen_urls;"
            var statement: OpaquePointer?
            guard sqlite3_prepare_v2(legacyDB, sql, -1, &statement, nil) == SQLITE_OK else { continue }
            defer { sqlite3_finalize(statement) }

            while sqlite3_step(statement) == SQLITE_ROW {
                if let url = stringColumn(statement, 0) {
                    insertSeenURL(url)
                }
            }
            return
        }
    }

    func upsert(_ job: Job, now: Date = .init()) -> JobChange {
        let iso = Self.iso(now)
        let existing = fetchByHash(job.hash)

        if let existing {
            if existing.status == "closed" {
                updateJob(existingID: existing.id, job: job, now: iso, status: "open")
                insertHistory(jobID: existing.id, field: "status", oldValue: "closed", newValue: "open", diff: nil, now: iso)
                linkSource(jobID: existing.id, source: job.source.rawValue, url: job.url, now: iso)
                return JobChange(jobID: existing.id, kind: .reopened, diff: nil, summary: "reopened")
            }

            let descriptionChanged = existing.description != job.description
            let titleChanged = existing.title != job.title
            if descriptionChanged || titleChanged {
                let diff = DiffEngine.lineDiff(old: existing.description, new: job.description)
                updateJob(existingID: existing.id, job: job, now: iso, status: "open")
                insertHistory(
                    jobID: existing.id,
                    field: descriptionChanged ? "description" : "title",
                    oldValue: existing.description,
                    newValue: job.description,
                    diff: diff.isEmpty ? nil : diff,
                    now: iso
                )
                linkSource(jobID: existing.id, source: job.source.rawValue, url: job.url, now: iso)
                return JobChange(jobID: existing.id, kind: .updated, diff: diff, summary: DiffEngine.summarize(diff))
            }

            touch(existingID: existing.id, now: iso)
            linkSource(jobID: existing.id, source: job.source.rawValue, url: job.url, now: iso)
            return JobChange(jobID: existing.id, kind: .unchanged, diff: nil, summary: nil)
        }

        let id = job.hash
        insertJob(id: id, job: job, now: iso)
        insertHistory(jobID: id, field: "created", oldValue: nil, newValue: job.title, diff: nil, now: iso)
        linkSource(jobID: id, source: job.source.rawValue, url: job.url, now: iso)
        insertSeenURL(job.url)
        return JobChange(jobID: id, kind: .new, diff: nil, summary: nil)
    }

    func closeMissing(seenIDs: Set<String>, now: Date = .init()) -> Int {
        let iso = Self.iso(now)
        let openIDs = fetchOpenIDs()
        var closed = 0
        for id in openIDs where !seenIDs.contains(id) {
            exec("UPDATE jobs SET status = 'closed', updated_at = ?, last_seen = ? WHERE id = ?", bind: { stmt in
                sqlite3_bind_text(stmt, 1, iso, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 2, iso, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 3, id, -1, SQLITE_TRANSIENT)
            })
            insertHistory(jobID: id, field: "status", oldValue: "open", newValue: "closed", diff: nil, now: iso)
            closed += 1
        }
        return closed
    }

    func openJobCount() -> Int {
        scalarInt("SELECT COUNT(*) FROM jobs WHERE status = 'open'") ?? 0
    }

    func trackedCount() -> Int {
        scalarInt("SELECT COUNT(*) FROM jobs") ?? 0
    }

    func containsURL(_ url: String) -> Bool {
        scalarInt("SELECT 1 FROM seen_urls WHERE url = ? LIMIT 1", bind: { stmt in
            sqlite3_bind_text(stmt, 1, url, -1, SQLITE_TRANSIENT)
        }) == 1
    }

    func insertSeenURL(_ url: String) {
        exec("INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", bind: { stmt in
            sqlite3_bind_text(stmt, 1, url, -1, SQLITE_TRANSIENT)
        })
    }

    func exportOpenJobs() -> [[String: String]] {
        guard let db else { return [] }
        let sql = """
        SELECT company, title, location, remote, url, source, status, first_seen, last_seen, description
        FROM jobs WHERE status = 'open' ORDER BY company, title
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else { return [] }
        defer { sqlite3_finalize(statement) }

        var rows: [[String: String]] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            rows.append([
                "company": stringColumn(statement, 0) ?? "",
                "title": stringColumn(statement, 1) ?? "",
                "location": stringColumn(statement, 2) ?? "",
                "remote": stringColumn(statement, 3) ?? "",
                "url": stringColumn(statement, 4) ?? "",
                "source": stringColumn(statement, 5) ?? "",
                "status": stringColumn(statement, 6) ?? "",
                "first_seen": stringColumn(statement, 7) ?? "",
                "last_seen": stringColumn(statement, 8) ?? "",
                "description": stringColumn(statement, 9) ?? "",
            ])
        }
        return rows
    }

    func exportHistory(since days: Int = 30) -> [[String: String]] {
        guard let db else { return [] }
        let sql = """
        SELECT job_id, changed_at, field, old_value, new_value, diff
        FROM history
        WHERE changed_at >= datetime('now', ?)
        ORDER BY changed_at DESC
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else { return [] }
        defer { sqlite3_finalize(statement) }
        let modifier = "-\(days) days"
        sqlite3_bind_text(statement, 1, modifier, -1, SQLITE_TRANSIENT)

        var rows: [[String: String]] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            rows.append([
                "job_id": stringColumn(statement, 0) ?? "",
                "changed_at": stringColumn(statement, 1) ?? "",
                "field": stringColumn(statement, 2) ?? "",
                "old_value": stringColumn(statement, 3) ?? "",
                "new_value": stringColumn(statement, 4) ?? "",
                "diff": stringColumn(statement, 5) ?? "",
            ])
        }
        return rows
    }

    func countJobs(company: String, since: String) -> Int {
        scalarInt(
            "SELECT COUNT(*) FROM jobs WHERE company = ? AND first_seen >= ?",
            bind: { stmt in
                sqlite3_bind_text(stmt, 1, company, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 2, since, -1, SQLITE_TRANSIENT)
            }
        ) ?? 0
    }

    func countOpenJobs(company: String) -> Int {
        scalarInt(
            "SELECT COUNT(*) FROM jobs WHERE company = ? AND status = 'open'",
            bind: { stmt in
                sqlite3_bind_text(stmt, 1, company, -1, SQLITE_TRANSIENT)
            }
        ) ?? 0
    }

    func averageLifetimeDays(company: String) -> Double {
        guard let db else { return 0 }
        let sql = """
        SELECT AVG(julianday(last_seen) - julianday(first_seen))
        FROM jobs WHERE company = ? AND status = 'closed'
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else { return 0 }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, company, -1, SQLITE_TRANSIENT)
        guard sqlite3_step(statement) == SQLITE_ROW else { return 0 }
        return sqlite3_column_double(statement, 0)
    }

    func countByRemote() -> (remote: Int, hybrid: Int, onsite: Int) {
        (
            scalarInt("SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'remote'") ?? 0,
            scalarInt("SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'hybrid'") ?? 0,
            scalarInt("SELECT COUNT(*) FROM jobs WHERE status = 'open' AND remote = 'onsite'") ?? 0
        )
    }

    func historyCount(field: String, sinceDays: Int) -> Int {
        scalarInt(
            """
            SELECT COUNT(*) FROM history
            WHERE field = ? AND changed_at >= datetime('now', ?)
            """,
            bind: { stmt in
                sqlite3_bind_text(stmt, 1, field, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 2, "-\(sinceDays) days", -1, SQLITE_TRANSIENT)
            }
        ) ?? 0
    }

    private struct StoredJob {
        let id: String
        let title: String
        let description: String?
        let status: String
    }

    private func fetchByHash(_ hash: String) -> StoredJob? {
        guard let db else { return nil }
        let sql = "SELECT id, title, description, status FROM jobs WHERE hash = ? LIMIT 1;"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else { return nil }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, hash, -1, SQLITE_TRANSIENT)
        guard sqlite3_step(statement) == SQLITE_ROW else { return nil }
        return StoredJob(
            id: stringColumn(statement, 0) ?? "",
            title: stringColumn(statement, 1) ?? "",
            description: stringColumn(statement, 2),
            status: stringColumn(statement, 3) ?? "open"
        )
    }

    private func fetchOpenIDs() -> [String] {
        guard let db else { return [] }
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, "SELECT id FROM jobs WHERE status = 'open'", -1, &statement, nil) == SQLITE_OK else {
            return []
        }
        defer { sqlite3_finalize(statement) }
        var ids: [String] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            if let id = stringColumn(statement, 0) { ids.append(id) }
        }
        return ids
    }

    private func insertJob(id: String, job: Job, now: String) {
        exec("INSERT OR IGNORE INTO companies (name) VALUES (?)", bind: { stmt in
            sqlite3_bind_text(stmt, 1, job.company, -1, SQLITE_TRANSIENT)
        })
        exec(
            """
            INSERT INTO jobs (
                id, company, title, location, remote, url, source, published_at,
                updated_at, first_seen, last_seen, status, description, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            bind: { stmt in
                sqlite3_bind_text(stmt, 1, id, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 2, job.company, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 3, job.title, -1, SQLITE_TRANSIENT)
                bindOptionalText(stmt, 4, job.location)
                bindOptionalText(stmt, 5, job.remote?.rawValue)
                sqlite3_bind_text(stmt, 6, job.url, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 7, job.source.rawValue, -1, SQLITE_TRANSIENT)
                bindOptionalText(stmt, 8, job.published.map(Self.iso))
                sqlite3_bind_text(stmt, 9, now, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 10, now, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 11, now, -1, SQLITE_TRANSIENT)
                bindOptionalText(stmt, 12, job.description)
                sqlite3_bind_text(stmt, 13, job.hash, -1, SQLITE_TRANSIENT)
            }
        )
    }

    private func updateJob(existingID: String, job: Job, now: String, status: String) {
        exec(
            """
            UPDATE jobs SET
                title = ?, location = ?, remote = ?, url = ?, source = ?,
                updated_at = ?, last_seen = ?, status = ?, description = ?
            WHERE id = ?
            """,
            bind: { stmt in
                sqlite3_bind_text(stmt, 1, job.title, -1, SQLITE_TRANSIENT)
                bindOptionalText(stmt, 2, job.location)
                bindOptionalText(stmt, 3, job.remote?.rawValue)
                sqlite3_bind_text(stmt, 4, job.url, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 5, job.source.rawValue, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 6, now, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 7, now, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 8, status, -1, SQLITE_TRANSIENT)
                bindOptionalText(stmt, 9, job.description)
                sqlite3_bind_text(stmt, 10, existingID, -1, SQLITE_TRANSIENT)
            }
        )
    }

    private func touch(existingID: String, now: String) {
        exec("UPDATE jobs SET updated_at = ?, last_seen = ? WHERE id = ?", bind: { stmt in
            sqlite3_bind_text(stmt, 1, now, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 2, now, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 3, existingID, -1, SQLITE_TRANSIENT)
        })
    }

    private func linkSource(jobID: String, source: String, url: String, now: String) {
        exec(
            "INSERT OR IGNORE INTO job_sources (job_id, source, source_url, seen_at) VALUES (?, ?, ?, ?)",
            bind: { stmt in
                sqlite3_bind_text(stmt, 1, jobID, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 2, source, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 3, url, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 4, now, -1, SQLITE_TRANSIENT)
            }
        )
    }

    private func insertHistory(
        jobID: String,
        field: String,
        oldValue: String?,
        newValue: String?,
        diff: String?,
        now: String
    ) {
        exec(
            """
            INSERT INTO history (job_id, changed_at, field, old_value, new_value, diff)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            bind: { stmt in
                sqlite3_bind_text(stmt, 1, jobID, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 2, now, -1, SQLITE_TRANSIENT)
                sqlite3_bind_text(stmt, 3, field, -1, SQLITE_TRANSIENT)
                bindOptionalText(stmt, 4, oldValue)
                bindOptionalText(stmt, 5, newValue)
                bindOptionalText(stmt, 6, diff)
            }
        )
    }

    private func exec(_ sql: String, bind: ((OpaquePointer?) -> Void)? = nil) {
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else { return }
        defer { sqlite3_finalize(statement) }
        bind?(statement)
        _ = sqlite3_step(statement)
    }

    private func scalarInt(_ sql: String, bind: ((OpaquePointer?) -> Void)? = nil) -> Int? {
        guard let db else { return nil }
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else { return nil }
        defer { sqlite3_finalize(statement) }
        bind?(statement)
        guard sqlite3_step(statement) == SQLITE_ROW else { return nil }
        return Int(sqlite3_column_int(statement, 0))
    }

    private func stringColumn(_ statement: OpaquePointer?, _ index: Int32) -> String? {
        guard let cString = sqlite3_column_text(statement, index) else { return nil }
        return String(cString: cString)
    }

    private static func iso(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: date)
    }

    private func bindOptionalText(_ statement: OpaquePointer?, _ index: Int32, _ value: String?) {
        if let value {
            sqlite3_bind_text(statement, index, value, -1, SQLITE_TRANSIENT)
        } else {
            sqlite3_bind_null(statement, index)
        }
    }
}

enum RepositoryError: Error, CustomStringConvertible {
    case openFailed(String)
    case execFailed(String)

    var description: String {
        switch self {
        case let .openFailed(message): "Repository open failed: \(message)"
        case let .execFailed(message): "Repository exec failed: \(message)"
        }
    }
}

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
