import Foundation

struct MonitorSummary: Sendable {
    let openVacancyCount: Int
    let trackedVacancyCount: Int
    let sourceCount: Int
    let failedSourceCount: Int
}

enum Telegram {
    static func notify(job: Job) async throws {
        let message = "🔔 \(job.company)\n\(job.title)\n\(job.url)"
        try await send(text: message)
    }

    static func notifyCheckComplete(summary: MonitorSummary) async throws {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "Europe/Kyiv")
        formatter.dateFormat = "dd MMM yyyy, HH:mm"
        let checkedAt = formatter.string(from: Date())

        let healthySourceCount = summary.sourceCount - summary.failedSourceCount
        let sourcesLine: String
        if summary.failedSourceCount == 0 {
            sourcesLine = "Sources: \(summary.sourceCount)/\(summary.sourceCount) OK"
        } else {
            sourcesLine = "Sources: \(healthySourceCount)/\(summary.sourceCount) OK (\(summary.failedSourceCount) failed)"
        }

        let message = """
        ✅ iOS Hunter

        No new iOS vacancies this run.

        Open roles now: \(summary.openVacancyCount)
        Tracking in total: \(summary.trackedVacancyCount)
        \(sourcesLine)

        Checked \(checkedAt) Kyiv
        """
        try await send(text: message)
    }

    static func send(text: String) async throws {
        let token = ProcessInfo.processInfo.environment["TELEGRAM_TOKEN"]
        let chatID = ProcessInfo.processInfo.environment["TELEGRAM_CHAT_ID"]

        guard let token, !token.isEmpty, let chatID, !chatID.isEmpty else {
            print(text)
            return
        }

        var components = URLComponents(string: "https://api.telegram.org/bot\(token)/sendMessage")!
        components.queryItems = [
            URLQueryItem(name: "chat_id", value: chatID),
            URLQueryItem(name: "text", value: text),
            URLQueryItem(name: "disable_web_page_preview", value: "true"),
        ]

        guard let url = components.url else {
            throw TelegramError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200 ... 299).contains(http.statusCode) else {
            throw TelegramError.sendFailed
        }
    }
}

enum TelegramError: Error {
    case invalidURL
    case sendFailed
}
