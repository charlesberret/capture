import Foundation

/// The drag-highlight state machine for the OCR span that becomes the note
/// body (LAB-239).
///
/// The load-bearing rule: **a selection that resolves to no text is not a
/// selection**. `hasSelection` is the single gate the UI uses — with it false,
/// the forward path ("Continue") must stay disabled, so saving without a
/// selection is refused by construction rather than by an if-statement in a
/// button handler.
struct SpanSelection: Equatable {
    let lines: [String]

    /// Index of the line where the current drag (or tap) began.
    private(set) var anchor: Int?
    /// Contiguous line range currently highlighted.
    private(set) var range: ClosedRange<Int>?

    init(text: String) {
        // OCR arrives as lines; keep blank lines as rows so the visual
        // selection maps 1:1 onto the source text.
        let raw = text.components(separatedBy: "\n")
        lines = raw.count == 1 && raw[0].isEmpty ? [] : raw
    }

    /// A drag or tap starts (or restarts) on a line.
    mutating func begin(at index: Int) {
        guard lines.indices.contains(index) else { return }
        anchor = index
        range = index...index
    }

    /// The finger moves to another line; the highlighted range grows or
    /// shrinks toward the finger, but stays contiguous around the anchor.
    mutating func drag(to index: Int) {
        guard let anchor, lines.indices.contains(index) else { return }
        let lo = min(anchor, index)
        let hi = max(anchor, index)
        range = lo...hi
    }

    /// The drag ends. A range whose lines carry no visible text is cleared —
    /// whitespace cannot become a note body.
    mutating func end() {
        guard range != nil else { return }
        if selectedText == nil {
            range = nil
            anchor = nil
        }
    }

    mutating func clear() {
        anchor = nil
        range = nil
    }

    /// The joined lines of the current range, trimmed. `nil` when there is
    /// no range or the range holds only whitespace — i.e. nothing to save.
    var selectedText: String? {
        guard let range else { return nil }
        let joined = lines[range].joined(separator: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return joined.isEmpty ? nil : joined
    }

    var hasSelection: Bool {
        selectedText != nil
    }

    /// Whether a given line index is inside the current highlight.
    func contains(_ index: Int) -> Bool {
        guard let range else { return false }
        return range.contains(index)
    }
}
