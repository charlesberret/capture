import SwiftUI

struct VoiceCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @StateObject private var recorder = AudioRecorder()
    @State private var proposal: NoteProposal?
    @State private var errorMessage: String?
    @State private var permissionDenied = false

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

            Text("The transcript goes to the confirm screen — nothing is written until you confirm.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Spacer()
        }
        .navigationTitle("Voice")
        .navigationDestination(item: $proposal) { proposal in
            ConfirmNoteView(proposal: proposal)
        }
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
                let transcript = try await appModel.transcribeOnly(from: url)
                proposal = try await appModel.proposeNote(for: transcript)
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
