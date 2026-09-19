import XCTest

@testable import Capture

/// LAB-239: the span-selection gate. These tests pin the load-bearing rule —
/// a selection that resolves to no text is not a selection, so the UI's
/// forward path cannot be enabled without a real span.
final class SpanSelectionTests: XCTestCase {
    private let page = """
    The Cypherpunk Mailing List as Unauthorized Workshop
    by Charles Berret

    Chapter draft: surveillance, remailers, and the
    social life of cryptography.

    Keywords: privacy, remailers, PGP
    """

    func testTapSelectsASingleLine() {
        var s = SpanSelection(text: page)
        s.begin(at: 0)
        s.end()
        XCTAssertEqual(s.selectedText, "The Cypherpunk Mailing List as Unauthorized Workshop")
        XCTAssertTrue(s.hasSelection)
    }

    func testDragDownwardIsContiguous() {
        var s = SpanSelection(text: page)
        s.begin(at: 3)
        s.drag(to: 4)
        s.end()
        XCTAssertEqual(
            s.selectedText,
            "Chapter draft: surveillance, remailers, and the\nsocial life of cryptography."
        )
    }

    func testDragUpwardIsTheSameRangeAsDownward() {
        var s = SpanSelection(text: page)
        s.begin(at: 4)
        s.drag(to: 3)
        s.end()
        let down: SpanSelection = {
            var d = SpanSelection(text: page)
            d.begin(at: 3)
            d.drag(to: 4)
            d.end()
            return d
        }()
        XCTAssertEqual(s.selectedText, down.selectedText)
    }

    func testWhitespaceOnlySelectionIsRefused() {
        let blank = "line one\n\n\nline two"
        var s = SpanSelection(text: blank)
        s.begin(at: 1)
        s.drag(to: 2)
        s.end()
        XCTAssertFalse(s.hasSelection, "whitespace cannot become a note body")
        XCTAssertNil(s.selectedText)
    }

    func testNoSelectionAtAllIsRefused() {
        var s = SpanSelection(text: page)
        s.end()
        XCTAssertFalse(s.hasSelection)
    }

    func testClearRemovesTheSelection() {
        var s = SpanSelection(text: page)
        s.begin(at: 0)
        s.drag(to: 2)
        s.end()
        XCTAssertTrue(s.hasSelection)
        s.clear()
        XCTAssertFalse(s.hasSelection)
    }

    func testOutOfRangeIndicesAreIgnored() {
        var s = SpanSelection(text: page)
        s.begin(at: 99)
        XCTAssertNil(s.range)
        s.drag(to: -3)
        XCTAssertEqual(s.range, nil)
    }

    func testOnlyTheSelectedSpanIsTheBodyNotTheWholePage() {
        var s = SpanSelection(text: page)
        s.begin(at: 6)
        s.end()
        XCTAssertNotEqual(s.selectedText, page.trimmingCharacters(in: .whitespacesAndNewlines))
        XCTAssertEqual(s.selectedText, "Keywords: privacy, remailers, PGP")
    }
}
