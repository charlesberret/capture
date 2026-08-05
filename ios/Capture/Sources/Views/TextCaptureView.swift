import SwiftUI

struct TextCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var text = ""
    @State private var result: CaptureResult?
    @State private var errorMessage: String?

    let onCapture: (String) async throws -> CaptureResult

    var body: some View {
        VStack(spacing: 16) {
            TextEditor(text: $text)
                .padding(8)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
                .padding()

            Button("Save Note") {
                Task { await submit() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || appModel.isProcessing)

            if let result {
                CaptureResultView(result: result)
                    .padding(.horizontal)
            }

            Spacer()
        }
        .navigationTitle("Text")
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
