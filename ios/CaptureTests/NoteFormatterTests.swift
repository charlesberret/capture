import XCTest

@testable import Capture

/// LAB-240: the iOS app writes the same YAML+md as the CLI. These tests
/// mirror the CLI's floor suite (`tests/test_capture_floor.py` and
/// `tests/test_note_contract.py`) so the two surfaces cannot drift:
/// filename contract, flow-sequence tags, scalar quoting, memo append.
final class NoteFormatterTests: XCTestCase {
    // MARK: - tag normalisation (mirror of the CLI's normalize_tag tests)

    func testNormalizeTagStripsLegacyBracketAndModelSpellings() {
        XCTAssertEqual(NoteFormatter.normalizeTag("kernel"), "kernel")
        XCTAssertEqual(NoteFormatter.normalizeTag("[[kernel]]"), "kernel")
        XCTAssertEqual(NoteFormatter.normalizeTag("[[llm:phi3]]"), "llm/phi3")
        XCTAssertEqual(NoteFormatter.normalizeTag("llm:qwen-capable"), "llm/qwen-capable")
        XCTAssertEqual(NoteFormatter.normalizeTag("  spaced  "), "spaced")
        XCTAssertNil(NoteFormatter.normalizeTag(""))
    }

    func testFormatTagsDedupesAndStripsSequenceBreakers() {
        // a comma or bracket inside a tag would split/short the flow sequence
        XCTAssertEqual(NoteFormatter.formatTags(["a", "a", "b,c", "[d]"]), "[a, bc, d]")
    }

    func testFormatTagsOutputIsAFlowSequenceWithNoBrackets() {
        let line = "tags: \(NoteFormatter.formatTags(["[[kernel]]", "[[captured]]", "[[llm:phi3]]"]))"
        XCTAssertTrue(line.hasPrefix("tags: [kernel, captured, llm/phi3]"))
        XCTAssertFalse(line.contains("[["))
    }

    // MARK: - scalar quoting (mirror of the CLI's yaml_scalar tests)

    func testYamlScalarQuotesAMetacharacterTitle() {
        let title = "[draft] thing"
        XCTAssertEqual(NoteFormatter.yamlScalar(title), "\"[draft] thing\"")
    }

    func testYamlScalarQuotesYesAndColons() {
        XCTAssertEqual(NoteFormatter.yamlScalar("yes"), "\"yes\"")
        XCTAssertEqual(NoteFormatter.yamlScalar("Artificial Metis: Beyond the Turing Test"),
                       "\"Artificial Metis: Beyond the Turing Test\"")
    }

    func testYamlScalarLeavesPlainTitlesBare() {
        XCTAssertEqual(NoteFormatter.yamlScalar("plain title"), "plain title")
    }

    // MARK: - the whole note

    func testBuildNoteFilenameMatchesTheCLIContract() {
        let (filename, _) = NoteFormatter.buildNote(
            content: "some captured thought",
            title: "A Test Note",
            tags: ["kernel", "captured"],
            author: "Charles Berret"
        )
        let parts = filename.components(separatedBy: " - ")
        XCTAssertEqual(parts.count, 2)
        XCTAssertEqual(parts[0].count, 12)
        XCTAssertNotNil(parts[0].range(of: "^[0-9]{12}$", options: .regularExpression))
        XCTAssertTrue(parts[1].hasSuffix(".md"))
    }

    func testBuildNoteFallsBackToTimestampOnlyForAnEmptySlug() {
        let (filename, body) = NoteFormatter.buildNote(
            content: "   ",
            title: "   ",
            tags: ["kernel"]
        )
        XCTAssertNotNil(filename.range(of: "^[0-9]{12}\\.md$", options: .regularExpression))
        XCTAssertTrue(body.contains("title: Untitled capture\n"))
    }

    func testBuildNoteFrontmatterCarriesTitleDateTagsAndAuthor() {
        let (filename, body) = NoteFormatter.buildNote(
            content: "some captured thought",
            title: "A Test Note",
            tags: ["kernel", "captured"],
            author: "Charles Berret"
        )
        _ = filename
        XCTAssertTrue(body.hasPrefix("---\n"))
        XCTAssertTrue(body.contains("title: A Test Note\nauthor: Charles Berret\n"))
        XCTAssertNotNil(body.range(of: #"date: \d{4}-\d{2}-\d{2} \d{2}:\d{2}"#, options: .regularExpression))
        XCTAssertTrue(body.contains("tags: [kernel, captured]\n"))
        XCTAssertTrue(body.contains("---\n\nsome captured thought\n"))
    }

    func testBuildNoteEmitsNoLegacyBracketTags() {
        let (_, body) = NoteFormatter.buildNote(
            content: "some captured thought",
            title: "A Test Note",
            tags: ["[[kernel]]", "[[captured]]", "[[llm:phi3]]"]
        )
        let tagsLine = body
            .components(separatedBy: "\n")
            .first { $0.hasPrefix("tags:") } ?? ""
        XCTAssertFalse(tagsLine.contains("[["))
    }

    // MARK: - the memo

    func testMemoAppendsWithABlankLineSeparator() {
        XCTAssertEqual(NoteFormatter.noteBody(content: "the capture", memo: "  a memo  "),
                       "the capture\n\na memo")
    }

    func testEmptyMemoLeavesTheBodyUntouched() {
        XCTAssertEqual(NoteFormatter.noteBody(content: "the capture", memo: "   "),
                       "the capture")
    }

    func testBuildNoteAppendsTheMemoToTheWrittenBody() {
        let (_, body) = NoteFormatter.buildNote(
            content: "some captured thought",
            title: "A Test Note",
            tags: ["kernel"],
            memo: "read this before the Tetrad sitting"
        )
        XCTAssertTrue(body.hasSuffix("some captured thought\n\nread this before the Tetrad sitting\n"))
    }
}
