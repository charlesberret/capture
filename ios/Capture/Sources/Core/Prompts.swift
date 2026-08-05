import Foundation

enum Prompts {
    static func load(_ name: String) -> String {
        let bundle = Bundle.main
        let base = name.replacingOccurrences(of: ".txt", with: "")
        if let url = bundle.url(forResource: base, withExtension: "txt", subdirectory: "Prompts"),
           let text = try? String(contentsOf: url, encoding: .utf8) {
            return text
        }
        // Fallback if subdirectory layout differs
        if let url = bundle.url(forResource: base, withExtension: "txt"),
           let text = try? String(contentsOf: url, encoding: .utf8) {
            return text
        }
        return fallback(name: base)
    }

    static func format(_ name: String, _ replacements: [String: String]) -> String {
        var text = load(name)
        for (key, value) in replacements {
            text = text.replacingOccurrences(of: "{\(key)}", with: value)
        }
        return text
    }

    private static func fallback(name: String) -> String {
        switch name {
        case "title":
            return """
            Generate a concise 3-8 word title for this note. Return ONLY the title on a single line.

            Note content:
            {content}

            Title:
            """
        case "tags":
            return """
            Suggest exactly 3 tags for this note. Return ONLY a comma-separated list on a single line.

            Note content:
            {content}

            Tags:
            """
        default:
            return "{content}"
        }
    }
}
