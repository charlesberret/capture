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

    func captureText(_ text: String) async throws -> CaptureResult {
        isProcessing = true
        statusMessage = "Creating note…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        let result = try await pipeline.createNote(from: text)
        lastResult = result
        return result
    }

    func captureVoice(from audioURL: URL) async throws -> CaptureResult {
        isProcessing = true
        statusMessage = "Transcribing…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        let text = try await pipeline.transcribeAudio(at: audioURL)
        statusMessage = "Creating note…"
        let result = try await pipeline.createNote(from: text)
        lastResult = result
        return result
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

}
