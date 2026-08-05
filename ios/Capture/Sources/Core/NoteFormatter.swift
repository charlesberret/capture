import Foundation

enum NoteFormatter {
    static func timestamp() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMddHHmm"
        return formatter.string(from: Date())
    }

    static func slugify(_ text: String, maxLength: Int = 50) -> String {
        let firstLine = text.split(separator: "\n", maxSplits: 1).first.map(String.init) ?? text
        var slug = String(firstLine.prefix(maxLength)).trimmingCharacters(in: .whitespacesAndNewlines)
        let forbidden = CharacterSet(charactersIn: "/\\:*?\"<>|")
        slug = slug.components(separatedBy: forbidden).joined()
        return slug.trimmingCharacters(in: CharacterSet(charactersIn: " ."))
    }

    static func displayDate() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter.string(from: Date())
    }

    static func buildNote(
        content: String,
        title: String,
        tags: [String],
        author: String = ""
    ) -> (filename: String, body: String) {
        let slug = slugify(title, maxLength: 80)
        let ts = timestamp()
        let filename = slug.isEmpty ? "\(ts).md" : "\(ts) - \(slug).md"
        let authorLine = author.isEmpty ? "" : "\nauthor: \(author)"
        let tagsLine = tags.joined(separator: ", ")
        let body = """
        ---
        title: \(slug.isEmpty ? "Untitled capture" : slug)\(authorLine)
        date: \(displayDate())
        tags: \(tagsLine)
        ---

        \(content)
        """
        return (filename, body)
    }
}
