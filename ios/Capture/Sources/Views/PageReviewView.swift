import SwiftUI

/// Shows extracted OCR text to the human before anything is written (LAB-238),
/// and lets them drag-highlight the span that will become the note body
/// (LAB-239). Only the highlighted span proceeds; the forward path stays
/// disabled until a real selection exists, so saving without one is refused.
///
/// No write happens in this view — the confirm step (LAB-240) owns the write.
struct PageReviewView: View {
    let ocrText: String
    let onRetake: () -> Void
    let onContinue: (String) -> Void

    @State private var selection: SpanSelection
    @State private var rowFrames: [Int: CGRect] = [:]

    init(
        ocrText: String,
        onRetake: @escaping () -> Void,
        onContinue: @escaping (String) -> Void
    ) {
        self.ocrText = ocrText
        self.onRetake = onRetake
        self.onContinue = onContinue
        _selection = State(initialValue: SpanSelection(text: ocrText))
    }

    var body: some View {
        VStack(spacing: 0) {
            Label("OCR read — nothing is written yet", systemImage: "eye")
                .foregroundStyle(.orange)
                .font(.headline)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding([.horizontal, .top])

            Text("Drag across the lines that should become the note body.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal)

            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(selection.lines.indices, id: \.self) { index in
                        Text(selection.lines[index])
                            .font(.body)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal)
                            .padding(.vertical, 6)
                            .background(
                                selection.contains(index)
                                    ? Color.accentColor.opacity(0.25)
                                    : Color.clear
                            )
                            .background(rowGeometry(index))
                            .contentShape(Rectangle())
                            .gesture(rowGesture(index))
                    }
                }
                .padding(.vertical, 8)
            }
            .coordinateSpace(name: "page")
            .onPreferenceChange(RowFramesKey.self) { frames in
                rowFrames = frames
            }

            Divider()

            if !selection.hasSelection {
                Label(
                    "Continue is refused until a span is highlighted.",
                    systemImage: "hand.raised"
                )
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }

            Button {
                if let span = selection.selectedText {
                    onContinue(span)
                }
            } label: {
                Label("Continue with Selected Span", systemImage: "checkmark.square")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal)
            .padding(.bottom)
            .disabled(!selection.hasSelection)
        }
        .navigationTitle("Highlight the Span")
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Discard", role: .destructive) {
                    onRetake()
                }
            }
        }
    }

    // MARK: - drag highlight plumbing

    /// Publishes each row's frame (in the "page" space) so a drag that starts
    /// on one row can hit-test the row under the finger as it moves.
    private func rowGeometry(_ index: Int) -> some View {
        GeometryReader { geo in
            Color.clear.preference(
                key: RowFramesKey.self,
                value: [index: geo.frame(in: .named("page"))]
            )
        }
    }

    private func rowGesture(_ index: Int) -> some Gesture {
        DragGesture(minimumDistance: 0, coordinateSpace: .named("page"))
            .onChanged { value in
                if value.translation == .zero {
                    selection.begin(at: index)
                } else if let row = row(at: value.location) {
                    selection.drag(to: row)
                }
            }
            .onEnded { _ in
                selection.end()
            }
    }

    private func row(at point: CGPoint) -> Int? {
        rowFrames.first { _, frame in frame.contains(point) }?.key
    }
}

/// Collects the frame of every OCR line row in the "page" coordinate space.
private struct RowFramesKey: PreferenceKey {
    static var defaultValue: [Int: CGRect] = [:]

    static func reduce(value: inout [Int: CGRect], nextValue: () -> [Int: CGRect]) {
        for (index, frame) in nextValue() {
            value[index] = frame
        }
    }
}
