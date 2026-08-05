import SwiftUI
import UIKit
import VisionKit

struct ScanCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var showScanner = false
    @State private var result: CaptureResult?
    @State private var errorMessage: String?

    let onCapture: (URL) async throws -> CaptureResult

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "doc.viewfinder")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Text("Scan a document with edge detection and OCR each page")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal)

            if VNDocumentCameraViewController.isSupported {
                Button("Scan Document") {
                    showScanner = true
                }
                .buttonStyle(.borderedProminent)
                .disabled(appModel.isProcessing)
            } else {
                Text("Document scanning is not available on this device.")
                    .foregroundStyle(.secondary)
            }

            if let result {
                CaptureResultView(result: result)
                    .padding()
            }

            Spacer()
        }
        .navigationTitle("Scan")
        .sheet(isPresented: $showScanner) {
            DocumentScannerView { pdfURL in
                showScanner = false
                Task { await processScan(at: pdfURL) }
            } onCancel: {
                showScanner = false
            }
        }
        .alert("Error", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private func processScan(at url: URL) async {
        do {
            result = try await onCapture(url)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct DocumentScannerView: UIViewControllerRepresentable {
    let onScan: (URL) -> Void
    let onCancel: () -> Void

    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let controller = VNDocumentCameraViewController()
        controller.delegate = context.coordinator
        return controller
    }

    func updateUIViewController(_ uiViewController: VNDocumentCameraViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onScan: onScan, onCancel: onCancel)
    }

    final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        let onScan: (URL) -> Void
        let onCancel: () -> Void

        init(onScan: @escaping (URL) -> Void, onCancel: @escaping () -> Void) {
            self.onScan = onScan
            self.onCancel = onCancel
        }

        func documentCameraViewControllerDidCancel(_ controller: VNDocumentCameraViewController) {
            onCancel()
        }

        func documentCameraViewController(
            _ controller: VNDocumentCameraViewController,
            didFailWithError error: Error
        ) {
            onCancel()
        }

        func documentCameraViewController(
            _ controller: VNDocumentCameraViewController,
            didFinishWith scan: VNDocumentCameraScan
        ) {
            let pdfURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("capture-scan-\(UUID().uuidString).pdf")
            // Render scan pages into a simple PDF via images processed by OCR path
            // VisionKit scan — pass first page images combined; use PDF from scan if available
            // VNDocumentCameraScan doesn't export PDF directly; we OCR page images
            Task {
                await exportScan(scan, to: pdfURL)
            }
        }

        @MainActor
        private func exportScan(_ scan: VNDocumentCameraScan, to pdfURL: URL) async {
            // Build a multi-page image bundle saved as temp files; pipeline OCRs PDF.
            // Since VNDocumentCameraScan has UIImages, write a combined text note path via temp PDF.
            // Simplest: OCR each page and join — delegate to pipeline via a temp multi-image approach.
            // For v1, OCR page 0 only if single page, else concatenate all pages as images in pipeline.
            // We'll write images to temp folder and OCR first page for now, then extend.
            // Better: create PDF from images using UIGraphicsPDFRenderer
            let renderer = UIGraphicsPDFRenderer(bounds: CGRect(x: 0, y: 0, width: 612, height: 792))
            do {
                try renderer.writePDF(to: pdfURL) { context in
                    for index in 0..<scan.pageCount {
                        let image = scan.imageOfPage(at: index)
                        context.beginPage()
                        let aspect = image.size.width / image.size.height
                        var drawRect = CGRect(x: 0, y: 0, width: 612, height: 792)
                        if aspect > 612.0 / 792.0 {
                            drawRect.size.height = 612 / aspect
                            drawRect.origin.y = (792 - drawRect.height) / 2
                        } else {
                            drawRect.size.width = 792 * aspect
                            drawRect.origin.x = (612 - drawRect.width) / 2
                        }
                        image.draw(in: drawRect)
                    }
                }
                onScan(pdfURL)
            } catch {
                onCancel()
            }
        }
    }
}
