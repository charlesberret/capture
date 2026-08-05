import SwiftUI

struct QuickCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var text = ""
    @State private var result: CaptureResult?
    @State private var errorMessage: String?

    let onCapture: (String) async throws -> CaptureResult

    var body: some View {
        VStack(spacing: 16) {
            TextField("What's your idea?", text: $text, axis: .vertical)
                .lineLimit(3...6)
                .textFieldStyle(.roundedBorder)
                .padding()

            Button("Capture") {
                Task { await submit() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || appModel.isProcessing)

            if let result {
                CaptureResultView(result: result)
                    .padding()
            }

            Spacer()
        }
        .navigationTitle("Quick")
        .alert("Error", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private func submit() async {
        do {
            result = try await onCapture(text)
            text = ""
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
