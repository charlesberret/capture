import SwiftUI

struct VoiceCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @StateObject private var recorder = AudioRecorder()
    @State private var result: CaptureResult?
    @State private var errorMessage: String?
    @State private var permissionDenied = false

    let onCapture: (URL) async throws -> CaptureResult

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: recorder.isRecording ? "waveform.circle.fill" : "mic.circle")
                .font(.system(size: 72))
                .foregroundStyle(recorder.isRecording ? .red : .accentColor)
                .symbolEffect(.pulse, isActive: recorder.isRecording)

            Text(recorder.isRecording ? "Recording… tap Stop when done" : "Tap to record a voice memo")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .padding(.horizontal)

            Button(recorder.isRecording ? "Stop & Transcribe" : "Record") {
                Task { await toggleRecording() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(appModel.isProcessing)

            if let result {
                CaptureResultView(result: result)
                    .padding()
            }

            Spacer()
        }
        .navigationTitle("Voice")
        .alert("Microphone Access", isPresented: $permissionDenied) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("Enable microphone access in Settings to record voice memos.")
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

    private func toggleRecording() async {
        if recorder.isRecording {
            guard let url = recorder.stop() else { return }
            do {
                result = try await onCapture(url)
            } catch {
                errorMessage = error.localizedDescription
            }
        } else {
            let granted = await recorder.requestPermission()
            guard granted else {
                permissionDenied = true
                return
            }
            do {
                try recorder.start()
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }
}
