import Foundation

enum NextDataHelpers {
    static func jsonData(from html: String) -> Data? {
        let pattern = #"<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
              let match = regex.firstMatch(in: html, range: NSRange(html.startIndex..., in: html)),
              let jsonRange = Range(match.range(at: 1), in: html)
        else {
            return nil
        }
        return String(html[jsonRange]).data(using: .utf8)
    }
}
