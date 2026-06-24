import Foundation
import zlib

struct EPAMSource: JobSource {
    let company = "EPAM"
    private let http: HTTPClient

    private let listURL = "https://careers.epam.com/en/jobs?search=iOS&specialization=developer"

    init(http: HTTPClient) {
        self.http = http
    }

    func fetchJobs() async throws -> [Job] {
        if let apiJobs = try? await fetchFromAPI(), !apiJobs.isEmpty {
            return apiJobs
        }
        return try await fetchFromSitemap()
    }

    private func fetchFromAPI() async throws -> [Job] {
        var allJobs: [Job] = []
        let pageSize = 50
        var page = 0

        while page < 20 {
            var components = URLComponents(string: "https://careers.epam.com/api/jobs/v2/search/global")!
            components.queryItems = [
                URLQueryItem(name: "lang", value: "en-us"),
                URLQueryItem(name: "sortBy", value: "relevance"),
                URLQueryItem(name: "q", value: "iOS"),
                URLQueryItem(name: "facets", value: "job_specialization=Developer"),
                URLQueryItem(name: "size", value: String(pageSize)),
                URLQueryItem(name: "from", value: String(page * pageSize)),
                URLQueryItem(name: "websiteLocale", value: "en-us"),
            ]

            guard let url = components.url else { break }

            let data = try await http.fetchData(
                from: url,
                headers: [
                    "Referer": listURL,
                    "Origin": "https://careers.epam.com",
                ],
                acceptableStatusCodes: 200 ..< 600
            )

            guard let response = try? JSONDecoder().decode(EPAMAPIResponse.self, from: data),
                  !response.jobs.isEmpty
            else {
                break
            }

            let mapped = response.jobs.compactMap { mapEPAMJob($0) }
            allJobs.append(contentsOf: mapped)

            if response.jobs.count < pageSize {
                break
            }
            page += 1
        }

        return deduplicated(allJobs)
    }

    private func fetchFromSitemap() async throws -> [Job] {
        let url = URL(string: "https://careers.epam.com/sitemap.xml.gz")!
        let data = try await http.fetchData(from: url)
        let xml = try xmlString(from: data)

        let pattern = #"<loc>(https://careers\.epam\.com/en/vacancy/[^<]+)</loc>"#
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            return []
        }

        let range = NSRange(xml.startIndex..., in: xml)
        var jobs: [Job] = []

        regex.enumerateMatches(in: xml, options: [], range: range) { match, _, _ in
            guard let match, let urlRange = Range(match.range(at: 1), in: xml) else { return }
            let jobURL = String(xml[urlRange])
            guard jobURL.localizedCaseInsensitiveContains("ios")
                || jobURL.localizedCaseInsensitiveContains("swift")
            else { return }

            let title = titleFromVacancyURL(jobURL)
            guard isIOSJob(title: title) else { return }
            jobs.append(Job(title: title, url: jobURL, company: company))
        }

        return deduplicated(jobs)
    }

    private func mapEPAMJob(_ job: EPAMJob) -> Job? {
        guard isIOSJob(title: job.name)
            || (job.primarySkill?.localizedCaseInsensitiveContains("iOS") == true)
        else {
            return nil
        }

        let path = job.seo?.url ?? "/en/vacancy/\(job.uid)"
        let jobURL = path.hasPrefix("http") ? path : "https://careers.epam.com\(path)"
        return Job(title: job.name, url: jobURL, company: company)
    }

    private func titleFromVacancyURL(_ url: String) -> String {
        guard let slug = url.split(separator: "/").last else { return url }
        let trimmed = slug
            .replacingOccurrences(of: #"blt[a-z0-9]+_en$"#, with: "", options: .regularExpression)
            .trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        return trimmed
            .split(separator: "-")
            .map { $0.capitalized }
            .joined(separator: " ")
    }

    private func deduplicated(_ jobs: [Job]) -> [Job] {
        var seen = Set<String>()
        return jobs.filter { seen.insert($0.url).inserted }
    }

    private func xmlString(from data: Data) throws -> String {
        if data.starts(with: [0x1F, 0x8B]) {
            return try gunzip(data)
        }
        guard let text = String(data: data, encoding: .utf8), text.contains("<loc>") else {
            throw EPAMSourceError.invalidSitemap
        }
        return text
    }

    private func gunzip(_ data: Data) throws -> String {
        let decompressed = try gunzipData(data)
        guard let text = String(data: decompressed, encoding: .utf8) else {
            throw EPAMSourceError.invalidSitemap
        }
        return text
    }

    private func gunzipData(_ data: Data) throws -> Data {
        try data.withUnsafeBytes { inputPointer in
            guard let inputBase = inputPointer.baseAddress?.assumingMemoryBound(to: Bytef.self) else {
                throw EPAMSourceError.invalidSitemap
            }

            var stream = z_stream()
            stream.next_in = UnsafeMutablePointer(mutating: inputBase)
            stream.avail_in = uInt(data.count)

            let initStatus = inflateInit2_(
                &stream,
                MAX_WBITS + 32,
                ZLIB_VERSION,
                Int32(MemoryLayout<z_stream>.size)
            )
            guard initStatus == Z_OK else {
                throw EPAMSourceError.invalidSitemap
            }
            defer { inflateEnd(&stream) }

            var output = Data()
            let chunkSize = 64 * 1024
            var status: Int32 = Z_OK

            repeat {
                var chunk = [UInt8](repeating: 0, count: chunkSize)
                status = chunk.withUnsafeMutableBytes { outputPointer in
                    guard let outputBase = outputPointer.bindMemory(to: Bytef.self).baseAddress else {
                        return Z_DATA_ERROR
                    }
                    stream.next_out = outputBase
                    stream.avail_out = uInt(chunkSize)
                    return inflate(&stream, Z_NO_FLUSH)
                }
                if status != Z_OK && status != Z_STREAM_END {
                    throw EPAMSourceError.invalidSitemap
                }
                output.append(chunk, count: chunkSize - Int(stream.avail_out))
                if status == Z_STREAM_END { break }
            } while stream.avail_out == 0

            return output
        }
    }
}

enum EPAMSourceError: Error {
    case invalidSitemap
}

private struct EPAMAPIResponse: Decodable {
    let jobs: [EPAMJob]
    let total: Int?

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        if let jobs = try? container.decode([EPAMJob].self, forKey: .jobs) {
            self.jobs = jobs
            self.total = try? container.decode(Int.self, forKey: .total)
            return
        }
        if let data = try? container.decode(EPAMDataContainer.self, forKey: .data) {
            jobs = data.jobs
            total = data.total
            return
        }
        jobs = []
        total = nil
    }

    private enum CodingKeys: String, CodingKey {
        case jobs
        case data
        case total
    }
}

private struct EPAMDataContainer: Decodable {
    let jobs: [EPAMJob]
    let total: Int?
}

private struct EPAMJob: Decodable {
    let uid: String
    let name: String
    let primarySkill: String?
    let seo: EPAMSEO?

    enum CodingKeys: String, CodingKey {
        case uid
        case name
        case primarySkill = "primary_skill"
        case seo
    }
}

private struct EPAMSEO: Decodable {
    let url: String?
}
