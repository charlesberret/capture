import SwiftUI

struct QuickCaptureView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var text = ""
    @State private var proposal: NoteProposal?
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 16) {
            TextField("What's your idea?", text: $text, axis: .vertical)
                .lineLimit(3...6)
                .textFieldStyle(.roundedBorder)
                .padding()

            Button("Propose Note") {
                Task { await propose() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || appModel.isProcessing)

            Text("Nothing is saved here — the agent drafts a title + tags and you confirm before the note is written.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Spacer()
        }
        .navigationTitle("Quick")
        .navigationDestination(item: $proposal) { proposal in
            ConfirmNoteView(proposal: proposal)
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

    private func propose() async {
        do {
            proposal = try await appModel.proposeNote(for: text)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
