import Foundation

/// Builds the note exactly like the Python CLI: `YYYYMMDDHHMM - Slug.md`
/// with YAML frontmatter whose `tags` are a flow sequence and whose scalars
/// are quoted when bare YAML would misparse them (LAB-240: the same YAML+md
/// as the CLI — mirror of `capture.core.note`).
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
        return slug.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: " ."))
    }

    static func displayDate() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter.string(from: Date())
    }

    /// Reduce a tag to the bare form used in the notes frontmatter contract:
    /// legacy ``[[wikilink]]`` and ``llm:model`` spellings become ``kernel`` /
    /// ``llm/gemini``; characters that would break a YAML flow sequence are
    /// dropped. Mirror of the CLI's `normalize_tag`.
    static func normalizeTag(_ raw: String) -> String? {
        var tag = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        while tag.hasPrefix("[[") && tag.hasSuffix("]]") {
            tag = String(tag.dropFirst(2).dropLast(2)).trimmingCharacters(in: .whitespaces)
        }
        tag = tag.replacingOccurrences(of: ":", with: "/")
        for character in "[]{}#&*\"'," {
            tag = tag.replacingOccurrences(of: String(character), with: "")
        }
        tag = tag.components(separatedBy: .whitespacesAndNewlines).joined(separator: " ")
        let trimmed = tag.trimmingCharacters(in: .whitespaces)
        return trimmed.isEmpty ? nil : trimmed
    }

    /// Serialise tags as a YAML flow sequence: ``[kernel, captured]``.
    /// Mirror of the CLI's `format_tags`.
    static func formatTags(_ tags: [String]) -> String {
        var seen: [String] = []
        for raw in tags {
            guard let tag = normalizeTag(raw), !seen.contains(tag) else { continue }
            seen.append(tag)
        }
        return "[" + seen.joined(separator: ", ") + "]"
    }

    /// Quote a frontmatter scalar when bare YAML would misparse it.
    /// Mirror of the CLI's `yaml_scalar`.
    static func yamlScalar(_ value: String) -> String {
        let text = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty {
            return "\"\""
        }
        let metacharacters = CharacterSet(charactersIn: "[]{}>|*&!%@`#-?:,'\"")
        let firstScalar = text.unicodeScalars.first!
        var needsQuote = metacharacters.contains(firstScalar)
        if !needsQuote {
            needsQuote = text.contains(": ") || text.hasSuffix(":")
        }
        if !needsQuote {
            let keywordLiterals = ["true", "false", "null", "yes", "no", "on", "off", "~"]
            needsQuote = keywordLiterals.contains(text.lowercased())
        }
        if needsQuote {
            let escaped = text
                .replacingOccurrences(of: "\\", with: "\\\\")
                .replacingOccurrences(of: "\"", with: "\\\"")
            return "\"" + escaped + "\""
        }
        return text
    }

    /// The note body: capture content first, then an optional short memo.
    static func noteBody(content: String, memo: String) -> String {
        let trimmedMemo = memo.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmedMemo.isEmpty ? content : content + "\n\n" + trimmedMemo
    }

    static func buildNote(
        content: String,
        title: String,
        tags: [String],
        author: String = "",
        memo: String = ""
    ) -> (filename: String, body: String) {
        let slug = slugify(title, maxLength: 80)
        let ts = timestamp()
        let filename = slug.isEmpty ? "\(ts).md" : "\(ts) - \(slug).md"
        let authorLine = author.isEmpty ? "" : "\nauthor: \(yamlScalar(author))"
        let body = noteBody(content: content, memo: memo)
        // The CLI's note ends with a newline after the body — match it exactly.
        let noteText = """
        ---
        title: \(yamlScalar(slug.isEmpty ? "Untitled capture" : slug))\(authorLine)
        date: \(displayDate())
        tags: \(formatTags(tags))
        ---

        \(body)
        """ + "\n"
        return (filename, noteText)
    }
}
