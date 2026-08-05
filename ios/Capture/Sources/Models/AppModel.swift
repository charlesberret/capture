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

    func captureImage(at imageURL: URL) async throws -> CaptureResult {
        isProcessing = true
        statusMessage = "Reading text…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        let text = try await pipeline.ocrImage(at: imageURL)
        statusMessage = "Creating note…"
        let result = try await pipeline.createNote(from: text)
        lastResult = result
        return result
    }

    func captureScan(at pdfURL: URL) async throws -> CaptureResult {
        isProcessing = true
        statusMessage = "Reading document…"
        defer {
            isProcessing = false
            statusMessage = nil
        }
        refreshPipeline()
        let text = try await pipeline.ocrPDF(at: pdfURL)
        statusMessage = "Creating note…"
        let result = try await pipeline.createNote(from: text)
        lastResult = result
        return result
    }
}
