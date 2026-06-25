import Foundation

enum WordPressREST {
    struct VacancyItem: Decodable {
        let link: String
        let title: RenderedString

        struct RenderedString: Decodable {
            let rendered: String
        }

        var plainTitle: String {
            title.rendered
                .replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
                .trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }
}
