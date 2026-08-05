import PhotosUI
import SwiftUI

struct PhotoCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var pickerItem: PhotosPickerItem?
    @State private var result: CaptureResult?
    @State private var errorMessage: String?

    let onCapture: (URL) async throws -> CaptureResult

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "photo.on.rectangle.angled")
                .font(.system(size: 64))
                .foregroundStyle(.tint)

            Text("Pick a photo to extract text with Apple Vision")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal)

            PhotosPicker(selection: $pickerItem, matching: .images) {
                Text("Choose Photo")
            }
            .buttonStyle(.borderedProminent)
            .disabled(appModel.isProcessing)

            if let result {
                CaptureResultView(result: result)
                    .padding()
            }

            Spacer()
        }
        .navigationTitle("Photo")
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
            result = try await onCapture(url)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
