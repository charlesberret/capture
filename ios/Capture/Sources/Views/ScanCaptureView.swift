import SwiftUI
import VisionKit

/// VisionKit document camera → Apple Vision OCR, shown to the human.
/// No note is written from this screen — only a later confirm step writes.
struct ScanCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var showScanner = false
    @State private var reviewText: String?
    @State private var proposal: NoteProposal?
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "doc.viewfinder")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Text("Scan a document with edge detection. Each page is OCR'd and the text is shown to you — nothing is written until you confirm.")
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

            Spacer()
        }
        .navigationTitle("Scan")
        .navigationDestination(item: $reviewText) { text in
            PageReviewView(
                ocrText: text,
                onRetake: { reviewText = nil },
                onContinue: { span in proposeAndContinue(body: span) }
            )
        }
        .navigationDestination(item: $proposal) { proposal in
            ConfirmNoteView(proposal: proposal)
        }
        .sheet(isPresented: $showScanner) {
            DocumentScannerView { pdfURL in
                showScanner = false
                Task { await runOCR(pdf: pdfURL) }
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

    private func runOCR(pdf url: URL) async {
        do {
            reviewText = try await appModel.ocrPDFOnly(at: url)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func proposeAndContinue(body: String) {
        Task {
            do {
                proposal = try await appModel.proposeNote(for: body)
            } catch {
                errorMessage = error.localizedDescription
            }
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
            Task {
                await exportScan(scan)
            }
        }

        @MainActor
        private func exportScan(_ scan: VNDocumentCameraScan) async {
            let pdfURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("capture-scan-\(UUID().uuidString).pdf")
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
