import Foundation

struct HTTPClient: Sendable {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func fetchString(
        from url: URL,
        headers: [String: String] = [:]
    ) async throws -> String {
        let data = try await fetchData(from: url, headers: headers)
        guard let text = String(data: data, encoding: .utf8) else {
            throw HTTPClientError.invalidResponse
        }
        return text
    }

    func fetchData(
        from url: URL,
        headers: [String: String] = [:],
        acceptableStatusCodes: Range<Int> = 200 ..< 300
    ) async throws -> Data {
        var lastError: Error?

        for attempt in 0 ..< 3 {
            do {
                return try await fetchDataOnce(
                    from: url,
                    headers: headers,
                    acceptableStatusCodes: acceptableStatusCodes
                )
            } catch let error as HTTPClientError {
                lastError = error
                guard case let .httpStatus(code) = error, (500 ... 599).contains(code), attempt < 2 else {
                    throw error
                }
                try await Task.sleep(nanoseconds: UInt64(400_000_000 * (attempt + 1)))
            }
        }

        throw lastError ?? HTTPClientError.invalidResponse
    }

    func fetchStringAllowingBotWall(
        from url: URL,
        headers: [String: String] = [:]
    ) async throws -> String? {
        do {
            return try await fetchString(from: url, headers: headers)
        } catch let error as HTTPClientError {
            guard case let .httpStatus(code) = error, code == 403 else {
                throw error
            }
            return nil
        }
    }

    private func fetchDataOnce(
        from url: URL,
        headers: [String: String],
        acceptableStatusCodes: Range<Int>
    ) async throws -> Data {
        var request = URLRequest(url: url)
        request.setValue(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            forHTTPHeaderField: "User-Agent"
        )
        request.setValue("application/json, text/html, */*", forHTTPHeaderField: "Accept")
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw HTTPClientError.invalidResponse
        }
        guard acceptableStatusCodes.contains(http.statusCode) else {
            throw HTTPClientError.httpStatus(http.statusCode)
        }
        return data
    }

    func postForm(
        to url: URL,
        fields: [String: String],
        headers: [String: String] = [:]
    ) async throws -> Data {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            forHTTPHeaderField: "User-Agent"
        )
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json, text/html, */*", forHTTPHeaderField: "Accept")
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        var components = URLComponents()
        components.queryItems = fields.map { URLQueryItem(name: $0.key, value: $0.value) }
        request.httpBody = components.percentEncodedQuery?.data(using: .utf8)

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw HTTPClientError.invalidResponse
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            throw HTTPClientError.httpStatus(http.statusCode)
        }
        return data
    }
}

enum HTTPClientError: Error, CustomStringConvertible {
    case invalidResponse
    case httpStatus(Int)

    var description: String {
        switch self {
        case .invalidResponse:
            "Invalid HTTP response"
        case let .httpStatus(code):
            "HTTP status \(code)"
        }
    }
}
