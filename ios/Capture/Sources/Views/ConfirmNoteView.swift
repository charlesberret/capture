import SwiftUI

/// The human gate before any note is written (LAB-240).
///
/// The agent's proposal (title + tags) arrives pre-filled but **editable**;
/// an optional short memo appends to the body. Nothing reaches the notes
/// folder except through this screen's "Confirm & Save" button — there is
/// no auto-save path anywhere in the app.
struct ConfirmNoteView: View {
    @EnvironmentObject private var appModel: AppModel
    @Environment(\.dismiss) private var dismiss

    let proposal: NoteProposal

    @State private var title: String
    @State private var tagsText: String
    @State private var memo = ""
    @State private var savedResult: CaptureResult?
    @State private var errorMessage: String?

    init(proposal: NoteProposal) {
        self.proposal = proposal
        _title = State(initialValue: proposal.proposedTitle)
        _tagsText = State(initialValue: proposal.proposedTags.joined(separator: ", "))
    }

    private var editedTags: [String] {
        tagsText
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    private var canConfirm: Bool {
        !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !appModel.isProcessing
    }

    var body: some View {
        Form {
            Section("Agent proposal — edit before saving") {
                LabeledContent("Title") {
                    TextField("Title", text: $title)
                        .multilineTextAlignment(.trailing)
                }
                LabeledContent("Tags") {
                    TextField("comma, separated", text: $tagsText)
                        .multilineTextAlignment(.trailing)
                }
            }

            Section("Body (as captured)") {
                Text(proposal.body)
                    .font(.callout)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            Section("Short memo (optional, appends to the body)") {
                TextField("A line of context for your future self", text: $memo, axis: .vertical)
                    .lineLimit(1...3)
            }

            if let savedResult {
                Section {
                    CaptureResultView(result: savedResult)
                        .listRowBackground(Color.clear)
                }
            }

            Section {
                Button {
                    Task { await save() }
                } label: {
                    Label("Confirm & Save", systemImage: "square.and.arrow.down")
                        .frame(maxWidth: .infinity)
                }
                .disabled(!canConfirm)
                if !canConfirm {
                    Text("Saving without a confirmed title is refused.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            } footer: {
                Text("The note is written only when you press Confirm & Save — exactly as the CLI writes it (YYYYMMDDHHMM - Title.md, YAML frontmatter).")
            }
        }
        .navigationTitle("Confirm Note")
        .alert("Error", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    private func save() async {
        do {
            savedResult = try await appModel.saveConfirmedNote(
                body: proposal.body,
                title: title,
                tags: editedTags,
                memo: memo
            )
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
