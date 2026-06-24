import Foundation

enum Telegram {
    static func notify(job: Job) async throws {
        let token = ProcessInfo.processInfo.environment["TELEGRAM_TOKEN"]
        let chatID = ProcessInfo.processInfo.environment["TELEGRAM_CHAT_ID"]

        let message = "🔔 \(job.company)\n\(job.title)\n\(job.url)"

        guard let token, !token.isEmpty, let chatID, !chatID.isEmpty else {
            print(message)
            return
        }

        var components = URLComponents(string: "https://api.telegram.org/bot\(token)/sendMessage")!
        components.queryItems = [
            URLQueryItem(name: "chat_id", value: chatID),
            URLQueryItem(name: "text", value: message),
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
