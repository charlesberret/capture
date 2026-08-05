import Foundation
import UIKit

@MainActor
final class CapturePipeline {
    private let config: CaptureConfig
    private let notesStore: NotesStore
    private let ocr = VisionOCRProvider()
    private let connections: KeywordConnectionsProvider

    init(config: CaptureConfig, notesStore: NotesStore) {
        self.config = config
        self.notesStore = notesStore
        self.connections = KeywordConnectionsProvider(
            maxKeywords: ProviderDefaults.maxKeywords,
            maxConnections: ProviderDefaults.maxConnections
        )
    }

    private var gemini: GeminiService? {
        guard let key = KeychainService.googleAPIKey, !key.isEmpty else { return nil }
        return GeminiService(apiKey: key, model: config.geminiModel)
    }

    func transcribeAudio(at url: URL) async throws -> String {
        guard config.providerName(for: .transcription) == "gemini_flash" else {
            throw CaptureError.transcriptionFailed
        }
        guard let gemini else { throw CaptureError.apiKeyMissing }
        let data = try Data(contentsOf: url)
        let mime = mimeType(for: url)
        let text = try await gemini.transcribeAudio(data: data, mimeType: mime)
        return text
    }

    func ocrImage(at url: URL) async throws -> String {
        guard let image = UIImage(contentsOfFile: url.path) else { throw CaptureError.ocrFailed }
        return try await ocr.extractText(from: image)
    }

    func ocrPDF(at url: URL) async throws -> String {
        return try await ocr.extractText(fromPDF: url)
    }

    func createNote(from content: String) async throws -> CaptureResult {
        let trimmed = content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { throw CaptureError.emptyContent }
        guard let notesURL = notesStore.resolvedURL else { throw CaptureError.notesFolderNotConfigured }

        let title = await generateTitle(for: trimmed)
        var tags = config.baseTags
        if config.metisEnabled {
            if let modelTag = modelTag() { tags.append(modelTag) }
            tags.append(contentsOf: await suggestTags(for: trimmed))
        }

        let (filename, body) = NoteFormatter.buildNote(
            content: trimmed,
            title: title,
            tags: tags,
            author: config.author
        )
        let fileURL = notesURL.appendingPathComponent(filename)
        do {
            try body.write(to: fileURL, atomically: true, encoding: .utf8)
        } catch {
            throw CaptureError.saveFailed(error.localizedDescription)
        }

        var related: [String] = []
        var serendipity: String?
        if config.metisEnabled && config.providerName(for: .connections) == "keyword" {
            related = connections.find(in: trimmed, notesDirectory: notesURL)
            serendipity = connections.serendipity(in: notesURL, ageDays: ProviderDefaults.serendipityAgeDays)
        }

        return CaptureResult(
            filename: filename,
            title: title,
            content: trimmed,
            tags: tags,
            connections: related,
            serendipity: serendipity
        )
    }

    private func generateTitle(for content: String) async -> String {
        if content.count <= config.contentThreshold {
            return NoteFormatter.slugify(content, maxLength: 80)
        }
        guard config.providerName(for: .title) == "gemini_flash", let gemini else {
            return NoteFormatter.slugify(content, maxLength: 80)
        }
        let prompt = Prompts.format("title", ["content": String(content.prefix(1000))])
        if let raw = try? await gemini.generateText(prompt: prompt) {
            var title = raw.trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
            if title.lowercased().hasPrefix("title:") {
                title = String(title.dropFirst(6)).trimmingCharacters(in: .whitespaces)
            }
            if !title.isEmpty && title.count < 80 {
                return NoteFormatter.slugify(title, maxLength: 80)
            }
        }
        return NoteFormatter.slugify(content, maxLength: 80)
    }

    private func suggestTags(for content: String) async -> [String] {
        guard config.providerName(for: .tags) == "gemini_flash", let gemini else { return [] }
        let prompt = Prompts.format("tags", ["content": String(content.prefix(500))])
        guard let raw = try? await gemini.generateText(prompt: prompt) else { return [] }
        return raw
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "\"'")) }
            .filter { !$0.isEmpty && $0.count < 30 }
            .map { "[[\($0)]]" }
    }

    private func modelTag() -> String? {
        guard config.providerName(for: .title) == "gemini_flash"
            || config.providerName(for: .tags) == "gemini_flash" else { return nil }
        let prefix = config.geminiModel.split(separator: "-").first.map(String.init) ?? "gemini"
        return "[[llm:\(prefix)]]"
    }

    private func mimeType(for url: URL) -> String {
        switch url.pathExtension.lowercased() {
        case "wav": "audio/wav"
        case "mp3": "audio/mp3"
        case "m4a": "audio/mp4"
        case "caf": "audio/x-caf"
        default: "audio/mp4"
        }
    }
}
