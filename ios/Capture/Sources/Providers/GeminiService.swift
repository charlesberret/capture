import Foundation

struct GeminiService {
    let apiKey: String
    let model: String
    let timeout: TimeInterval

    init(apiKey: String, model: String = ProviderDefaults.geminiModel, timeout: TimeInterval = 60) {
        self.apiKey = apiKey
        self.model = model
        self.timeout = timeout
    }

    func generateText(prompt: String) async throws -> String {
        let contents: [[String: Any]] = [
            ["parts": [["text": prompt]]]
        ]
        return try await generate(contents: contents)
    }

    func transcribeAudio(data: Data, mimeType: String, vocabularyHint: String? = nil) async throws -> String {
        let hint = vocabularyHint.map { "\nVocabulary context: \($0)" } ?? ""
        let prompt = """
        Transcribe this audio recording accurately. \
        Return ONLY the transcription text, no commentary or labels.\(hint)
        """
        let base64 = data.base64EncodedString()
        let contents: [[String: Any]] = [
            [
                "parts": [
                    ["text": prompt],
                    ["inline_data": ["mime_type": mimeType, "data": base64]],
                ]
            ]
        ]
        return try await generate(contents: contents)
    }

    private func generate(contents: [[String: Any]]) async throws -> String {
        guard !apiKey.isEmpty else { throw CaptureError.apiKeyMissing }

        let url = URL(string: "https://generativelanguage.googleapis.com/v1beta/models/\(model):generateContent?key=\(apiKey)")!
        var request = URLRequest(url: url, timeoutInterval: timeout)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["contents": contents])

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw CaptureError.saveFailed("Invalid response")
        }
        guard (200...299).contains(http.statusCode) else {
            let detail = String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"
            throw CaptureError.saveFailed(detail)
        }

        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard
            let candidates = json?["candidates"] as? [[String: Any]],
            let first = candidates.first,
            let content = first["content"] as? [String: Any],
            let parts = content["parts"] as? [[String: Any]]
        else {
            throw CaptureError.saveFailed("No text in Gemini response")
        }

        let text = parts.compactMap { $0["text"] as? String }.joined().trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { throw CaptureError.saveFailed("Empty Gemini response") }
        return text
    }
}
