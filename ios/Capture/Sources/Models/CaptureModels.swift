import Foundation

enum CaptureStage: String, CaseIterable, Codable {
    case transcription
    case ocr
    case title
    case tags
    case correction
    case connections
}

struct ProviderDefaults {
    static let geminiModel = "gemini-2.0-flash"
    static let contentThreshold = 30
    static let baseTags = ["[[kernel]]", "[[captured]]"]
    static let serendipityAgeDays = 30
    static let maxConnections = 3
    static let maxKeywords = 10

    /// Mirrors capture/platforms/ios.defaults.yaml
    static let stageProviders: [CaptureStage: String] = [
        .transcription: "gemini_flash",
        .ocr: "apple_vision",
        .title: "gemini_flash",
        .tags: "gemini_flash",
        .correction: "disabled",
        .connections: "keyword",
    ]
}

struct CaptureConfig {
    var notesFolderName: String = "Notes"
    var contentThreshold: Int = ProviderDefaults.contentThreshold
    var baseTags: [String] = ProviderDefaults.baseTags
    var author: String = ""
    var geminiModel: String = ProviderDefaults.geminiModel
    var stageProviders: [CaptureStage: String] = ProviderDefaults.stageProviders
    var metisEnabled: Bool = true

    func providerName(for stage: CaptureStage) -> String {
        stageProviders[stage] ?? ProviderDefaults.stageProviders[stage] ?? "disabled"
    }

    var usesGemini: Bool {
        stageProviders.values.contains("gemini_flash")
    }
}

enum CaptureMode: String, CaseIterable, Identifiable {
    case quick
    case text
    case voice
    case photo
    case scan

    var id: String { rawValue }

    var title: String {
        switch self {
        case .quick: "Quick"
        case .text: "Text"
        case .voice: "Voice"
        case .photo: "Photo"
        case .scan: "Scan"
        }
    }

    var subtitle: String {
        switch self {
        case .quick: "One-liner idea"
        case .text: "Longer note"
        case .voice: "Record & transcribe"
        case .photo: "OCR from image"
        case .scan: "Document scanner"
        }
    }

    var systemImage: String {
        switch self {
        case .quick: "bolt.fill"
        case .text: "text.alignleft"
        case .voice: "mic.fill"
        case .photo: "photo.fill"
        case .scan: "doc.viewfinder.fill"
        }
    }
}

struct CaptureResult: Identifiable {
    let id = UUID()
    let filename: String
    let title: String
    let content: String
    let tags: [String]
    let connections: [String]
    let serendipity: String?
}

enum CaptureError: LocalizedError {
    case notesFolderNotConfigured
    case apiKeyMissing
    case transcriptionFailed
    case ocrFailed
    case emptyContent
    case saveFailed(String)

    var errorDescription: String? {
        switch self {
        case .notesFolderNotConfigured:
            "Choose a Notes folder in Settings before capturing."
        case .apiKeyMissing:
            "Add your Google API key in Settings to use Gemini."
        case .transcriptionFailed:
            "Could not transcribe the recording."
        case .ocrFailed:
            "Could not extract text from the image."
        case .emptyContent:
            "Nothing to capture."
        case .saveFailed(let detail):
            "Failed to save note: \(detail)"
        }
    }
}
