import Foundation
import Vision
import UIKit

struct VisionOCRProvider {
    func extractText(from image: UIImage) async throws -> String {
        guard let cgImage = image.cgImage else { throw CaptureError.ocrFailed }

        return try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let observations = request.results as? [VNRecognizedTextObservation] ?? []
                let lines = observations.compactMap { $0.topCandidates(1).first?.string }
                let text = lines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
                if text.isEmpty {
                    continuation.resume(throwing: CaptureError.ocrFailed)
                } else {
                    continuation.resume(returning: text)
                }
            }
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }

    func extractText(fromPDF url: URL) async throws -> String {
        guard let document = CGPDFDocument(url as CFURL) else { throw CaptureError.ocrFailed }
        let pageCount = document.numberOfPages
        var allLines: [String] = []

        for pageIndex in 1...pageCount {
            guard let page = document.page(at: pageIndex) else { continue }
            let mediaBox = page.getBoxRect(.mediaBox)
            let width = Int(mediaBox.width * 2)
            let height = Int(mediaBox.height * 2)

            let colorSpace = CGColorSpaceCreateDeviceRGB()
            guard let context = CGContext(
                data: nil,
                width: width,
                height: height,
                bitsPerComponent: 8,
                bytesPerRow: width * 4,
                space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
            ) else { continue }

            context.setFillColor(UIColor.white.cgColor)
            context.fill(CGRect(x: 0, y: 0, width: width, height: height))
            context.scaleBy(x: 2, y: 2)
            context.drawPDFPage(page)

            guard let cgImage = context.makeImage() else { continue }
            let pageText = try await extractText(from: UIImage(cgImage: cgImage))
            if pageCount > 1 {
                allLines.append("[Page \(pageIndex)]")
            }
            allLines.append(pageText)
        }

        let result = allLines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
        guard !result.isEmpty else { throw CaptureError.ocrFailed }
        return result
    }
}
