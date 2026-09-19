import XCTest

/// LAB-238/239/240 dogfood: drives the real app in the simulator through the
/// photo loop — **see the OCR**, confirm nothing is written, drag-highlight a
/// span, and reach the confirm gate. Screenshots attach at each stage.
///
/// The system photo picker cannot complete on a fresh simulator (Photos
/// onboarding blocks library access), so the fixture image is injected via a
/// DEBUG launch argument (`-uitestInjectFixturePhoto`). Everything after the
/// pick is the real product: Vision OCR, review screen, drag-highlight,
/// confirm gate, and the loud failure when no Notes folder is configured.
/// `testFullPickerLoopOnDevice` keeps the honest end-to-end picker path for
/// devices and prepared simulators.
final class CaptureUITests: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    func testPhotoLoopShowsOCRAndGatesTheWrite() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-uitestInjectFixturePhoto"]
        app.launch()

        // Photo mode (list rows expose "Title, subtitle" labels)
        let photoButton = app.buttons.matching(
            NSPredicate(format: "label BEGINSWITH 'Photo'")
        ).firstMatch
        XCTAssertTrue(photoButton.waitForExistence(timeout: 10), "Photo row should exist")
        photoButton.tap()

        // LAB-238: the OCR is shown, under an explicit nothing-written banner.
        let banner = app.staticTexts["OCR read — nothing is written yet"]
        XCTAssertTrue(banner.waitForExistence(timeout: 30), "OCR should be shown to the human")

        var attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "01-ocr-shown"
        attachment.lifetime = .keepAlways
        add(attachment)

        // LAB-239: continuing without a selection is refused.
        let continueButton = app.buttons["Continue with Selected Span"]
        XCTAssertFalse(continueButton.isEnabled, "continue must be refused with no span")

        // Drag-highlight two OCR lines: the span becomes the body.
        let startLine = app.staticTexts["Chapter draft: surveillance, remailers, and the"]
        let endLine = app.staticTexts["social life of cryptography."]
        XCTAssertTrue(startLine.waitForExistence(timeout: 10), "OCR line should be a row")
        startLine.press(forDuration: 0.3, thenDragTo: endLine)

        attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "02-span-highlighted"
        attachment.lifetime = .keepAlways
        add(attachment)

        XCTAssertTrue(continueButton.isEnabled, "the highlighted span must unlock continue")
        continueButton.tap()

        // LAB-240: the confirm gate — the agent proposes, the human confirms.
        let confirmHeader = app.staticTexts["Agent proposal — edit before saving"]
        XCTAssertTrue(confirmHeader.waitForExistence(timeout: 15), "confirm screen should appear")
        XCTAssertTrue(app.buttons["Confirm & Save"].exists, "the only write path is the confirm button")

        attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "03-confirm-gate"
        attachment.lifetime = .keepAlways
        add(attachment)

        // Without a Notes folder configured, even a confirmed save must fail
        // loudly (no silent half-write). The gate itself is the evidence.
        app.buttons["Confirm & Save"].tap()
        let alert = app.alerts["Error"]
        XCTAssertTrue(
            alert.waitForExistence(timeout: 15),
            "saving without a configured notes folder must fail loudly, not silently"
        )
    }

    /// The full end-to-end picker path. Runs only when the environment asks
    /// for it (device, or a simulator whose Photos onboarding is complete).
    func testFullPickerLoopOnDevice() throws {
        try XCTSkipUnless(
            ProcessInfo.processInfo.environment["RUN_PICKER_TEST"] == "1",
            "Requires a device or a simulator with a fully onboarded photo library."
        )

        let app = XCUIApplication()
        app.launch()

        let photoButton = app.buttons.matching(
            NSPredicate(format: "label BEGINSWITH 'Photo'")
        ).firstMatch
        XCTAssertTrue(photoButton.waitForExistence(timeout: 10), "Photo row should exist")
        photoButton.tap()

        let library = app.buttons["Choose from Library"]
        XCTAssertTrue(library.waitForExistence(timeout: 10), "library door should exist")
        library.tap()

        let grid = app.collectionViews.firstMatch
        XCTAssertTrue(grid.waitForExistence(timeout: 10), "picker grid should appear")

        let loadingText = app.staticTexts["Loading..."]
        if loadingText.exists {
            let gone = NSPredicate(format: "exists == 0")
            let loaded = expectation(for: gone, evaluatedWith: loadingText)
            wait(for: [loaded], timeout: 40)
        }

        let firstCell = grid.cells.element(boundBy: 0)
        XCTAssertTrue(firstCell.waitForExistence(timeout: 10), "a photo cell should load")
        firstCell.tap()

        let addButton = app.buttons.matching(
            NSPredicate(format: "label BEGINSWITH 'Add'")
        ).firstMatch
        XCTAssertTrue(addButton.waitForExistence(timeout: 10), "Add should appear after selecting")
        addButton.tap()

        let banner = app.staticTexts["OCR read — nothing is written yet"]
        XCTAssertTrue(banner.waitForExistence(timeout: 30), "OCR should be shown to the human")
    }

    /// One-time simulator prep: dismiss the Photos first-launch onboarding
    /// so the system photo picker can read the library. Not a product test.
    func testZPreparePhotoLibraryOnboarding() {
        let photos = XCUIApplication(bundleIdentifier: "com.apple.mobileslideshow")
        photos.launch()
        for label in ["Continue", "Get Started", "OK", "Not Now", "Skip"] {
            let b = photos.buttons[label]
            if b.waitForExistence(timeout: 8) {
                b.tap()
            }
        }
        let cont = photos.buttons["Continue"]
        while cont.waitForExistence(timeout: 5) {
            cont.tap()
        }
    }
}
