import Foundation
import SQLite3

final class Store: Sendable {
    private nonisolated(unsafe) let db: OpaquePointer?

    init(path: String) throws {
        let directory = (path as NSString).deletingLastPathComponent
        if !directory.isEmpty {
            try FileManager.default.createDirectory(
                atPath: directory,
                withIntermediateDirectories: true
            )
        }

        var database: OpaquePointer?
        if sqlite3_open(path, &database) != SQLITE_OK {
            throw StoreError.openFailed(String(cString: sqlite3_errmsg(database)))
        }
        db = database

        let sql = "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY NOT NULL);"
        if sqlite3_exec(db, sql, nil, nil, nil) != SQLITE_OK {
            throw StoreError.execFailed(String(cString: sqlite3_errmsg(db)))
        }
    }

    deinit {
        sqlite3_close(db)
    }

    func contains(url: String) -> Bool {
        guard let db else { return false }
        let sql = "SELECT 1 FROM seen_urls WHERE url = ? LIMIT 1;"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return false
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, url, -1, SQLITE_TRANSIENT)
        return sqlite3_step(statement) == SQLITE_ROW
    }

    func insert(url: String) throws {
        guard let db else { throw StoreError.closed }
        let sql = "INSERT OR IGNORE INTO seen_urls (url) VALUES (?);"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw StoreError.execFailed(String(cString: sqlite3_errmsg(db)))
        }
        defer { sqlite3_finalize(statement) }
        sqlite3_bind_text(statement, 1, url, -1, SQLITE_TRANSIENT)
        if sqlite3_step(statement) != SQLITE_DONE {
            throw StoreError.execFailed(String(cString: sqlite3_errmsg(db)))
        }
    }

    func trackedVacancyCount() -> Int {
        guard let db else { return 0 }
        let sql = "SELECT COUNT(*) FROM seen_urls;"
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return 0
        }
        defer { sqlite3_finalize(statement) }
        guard sqlite3_step(statement) == SQLITE_ROW else { return 0 }
        return Int(sqlite3_column_int(statement, 0))
    }
}

enum StoreError: Error, CustomStringConvertible {
    case openFailed(String)
    case execFailed(String)
    case closed

    var description: String {
        switch self {
        case let .openFailed(message):
            "SQLite open failed: \(message)"
        case let .execFailed(message):
            "SQLite exec failed: \(message)"
        case .closed:
            "SQLite database is closed"
        }
    }
}

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
