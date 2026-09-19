import SwiftUI

/// Shows extracted OCR text to the human before anything is written.
///
/// The photo/scan loop is deliberately read-only at this stage: the OCR is
/// *shown*, and no note exists until the human confirms one in a later step.
/// There is no save path in this view on purpose.
struct PageReviewView: View {
    let ocrText: String
    let onRetake: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            Label("OCR read — nothing is written yet", systemImage: "eye")
                .foregroundStyle(.orange)
                .font(.headline)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()

            ScrollView {
                Text(ocrText)
                    .font(.body)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal)
            }

            Label(
                "The note is written only after you confirm it.",
                systemImage: "hand.raised"
            )
            .font(.caption)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .navigationTitle("Review OCR")
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Discard", role: .destructive) {
                    onRetake()
                }
            }
        }
    }
}
