import PhotosUI
import SwiftUI
import VisionKit

/// Photograph (VisionKit camera) or pick a page; Apple Vision OCR is *shown*
/// to the human. No note is written from this screen — the write happens only
/// after a later confirm step.
struct PhotoCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var pickerItem: PhotosPickerItem?
    @State private var showCamera = false
    @State private var reviewText: String?
    @State private var proposal: NoteProposal?
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "camera.viewfinder")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Text("Photograph or pick a page. Apple Vision reads the text and shows it to you — nothing is written until you confirm.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal)

            if VNDocumentCameraViewController.isSupported {
                Button {
                    showCamera = true
                } label: {
                    Label("Photograph a Page", systemImage: "camera")
                }
                .buttonStyle(.borderedProminent)
                .disabled(appModel.isProcessing)
            } else {
                Text("Camera not available on this device — use the library instead.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            PhotosPicker(selection: $pickerItem, matching: .images) {
                Label("Choose from Library", systemImage: "photo")
            }
            .buttonStyle(.bordered)
            .disabled(appModel.isProcessing)

            Spacer()
        }
        .navigationTitle("Photo")
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
        .sheet(isPresented: $showCamera) {
            DocumentScannerView { pdfURL in
                showCamera = false
                Task { await runOCR(pdf: pdfURL) }
            } onCancel: {
                showCamera = false
            }
        }
        .onChange(of: pickerItem) { _, newItem in
            guard let newItem else { return }
            Task { await process(item: newItem) }
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

    private func process(item: PhotosPickerItem) async {
        do {
            guard let data = try await item.loadTransferable(type: Data.self) else {
                throw CaptureError.ocrFailed
            }
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("capture-photo-\(UUID().uuidString).jpg")
            try data.write(to: url)
            reviewText = try await appModel.ocrImageOnly(at: url)
        } catch {
            errorMessage = error.localizedDescription
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
