import Foundation

struct KeywordConnectionsProvider {
    let maxKeywords: Int
    let maxConnections: Int

    func find(in content: String, notesDirectory: URL) -> [String] {
        let words = content.lowercased().split { !$0.isLetter && !$0.isNumber }
        let keywords = words.filter { $0.count > 5 }.prefix(maxKeywords)
        guard !keywords.isEmpty else { return [] }

        guard let files = try? FileManager.default.contentsOfDirectory(
            at: notesDirectory,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else { return [] }

        var connections: [String] = []
        for file in files where file.pathExtension == "md" && !file.lastPathComponent.hasPrefix("_") {
            guard let text = try? String(contentsOf: file, encoding: .utf8).lowercased() else { continue }
            let matches = keywords.filter { text.contains($0) }.count
            if matches >= 2 {
                var title = file.deletingPathExtension().lastPathComponent
                if let range = title.range(of: " - ") {
                    title = String(title[range.upperBound...])
                }
                connections.append(title)
                if connections.count >= maxConnections { break }
            }
        }
        return connections
    }

    func serendipity(in notesDirectory: URL, ageDays: Int) -> String? {
        let cutoff = Date().addingTimeInterval(-Double(ageDays) * 86_400)
        guard let files = try? FileManager.default.contentsOfDirectory(
            at: notesDirectory,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else { return nil }

        let oldNotes = files.filter { url in
            guard url.pathExtension == "md", !url.lastPathComponent.hasPrefix("_") else { return false }
            guard let values = try? url.resourceValues(forKeys: [.contentModificationDateKey]),
                  let modified = values.contentModificationDate else { return false }
            return modified < cutoff
        }
        guard let selected = oldNotes.randomElement() else { return nil }

        var title = selected.deletingPathExtension().lastPathComponent
        if let range = title.range(of: " - ") {
            title = String(title[range.upperBound...])
        }
        if let text = try? String(contentsOf: selected, encoding: .utf8) {
            let preview = text
                .split(separator: "\n")
                .map { $0.trimmingCharacters(in: .whitespaces) }
                .first { !$0.isEmpty && !$0.hasPrefix("---") }
                .map { String($0.prefix(100)) } ?? ""
            return "💡 Serendipity: \(title)\n   \(preview)..."
        }
        return "💡 Serendipity: \(title)"
    }
}
