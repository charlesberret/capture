import Foundation
import SwiftUI

@MainActor
final class AppModel: ObservableObject {
    @Published var config = CaptureConfig()
    @Published var notesStore = NotesStore()
    @Published var lastResult: CaptureResult?
    @Published var isProcessing = false
    @Published var statusMessage: String?

    private lazy var pipeline = CapturePipeline(config: config, notesStore: notesStore)

    func refreshPipeline() {
        pipeline = CapturePipeline(config: config, notesStore: notesStore)
    }

    /// Transcribe audio **without writing anything** — the transcript goes
    /// to the confirm screen.
    func transcribeOnly(from audioURL: URL) async throws -> String {
        isProcessing = true
        statusMessage = "Transcribing…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        return try await pipeline.transcribeAudio(at: audioURL)
    }

    /// OCR an image and **show the text to the human without writing anything**.
    func ocrImageOnly(at imageURL: URL) async throws -> String {
        isProcessing = true
        statusMessage = "Reading text…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        return try await pipeline.ocrImage(at: imageURL)
    }

    /// OCR a scanned document and **show the text without writing anything**.
    func ocrPDFOnly(at pdfURL: URL) async throws -> String {
        isProcessing = true
        statusMessage = "Reading document…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        return try await pipeline.ocrPDF(at: pdfURL)
    }

    /// Draft a title + tags proposal for a body. Writes nothing — the confirm
    /// screen owns the only write path.
    func proposeNote(for body: String) async throws -> NoteProposal {
        isProcessing = true
        statusMessage = "Drafting title & tags…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        return try await pipeline.proposeNote(for: body)
    }

    /// Write the note the human just confirmed (title/tags/memo may be their
    /// edits of the proposal). This is the app's only write.
    func saveConfirmedNote(
        body: String,
        title: String,
        tags: [String],
        memo: String
    ) async throws -> CaptureResult {
        isProcessing = true
        statusMessage = "Saving note…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        let result = try await pipeline.writeConfirmedNote(
            body: body,
            title: title,
            tags: tags,
            memo: memo
        )
        lastResult = result
        return result
    }
}
