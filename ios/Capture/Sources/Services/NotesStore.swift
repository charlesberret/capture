import Foundation

@MainActor
final class NotesStore: ObservableObject {
    @Published private(set) var resolvedURL: URL?
    @Published private(set) var displayPath: String = "Not configured"

    private let bookmarkKey = "net.berret.capture.notes-folder-bookmark"

    init() {
        restoreBookmark()
    }

    func setFolder(_ url: URL) {
        do {
            let bookmark = try url.bookmarkData(
                options: [],
                includingResourceValuesForKeys: nil,
                relativeTo: nil
            )
            UserDefaults.standard.set(bookmark, forKey: bookmarkKey)
            resolvedURL = url
            displayPath = url.lastPathComponent
            _ = url.startAccessingSecurityScopedResource()
        } catch {
            resolvedURL = nil
            displayPath = "Failed to save folder"
        }
    }

    func restoreBookmark() {
        guard let bookmark = UserDefaults.standard.data(forKey: bookmarkKey) else {
            resolvedURL = nil
            displayPath = "Not configured"
            return
        }
        var stale = false
        do {
            let url = try URL(
                resolvingBookmarkData: bookmark,
                options: [],
                relativeTo: nil,
                bookmarkDataIsStale: &stale
            )
            _ = url.startAccessingSecurityScopedResource()
            resolvedURL = url
            displayPath = url.path
            if stale {
                setFolder(url)
            }
        } catch {
            resolvedURL = nil
            displayPath = "Not configured"
        }
    }

    func clearFolder() {
        UserDefaults.standard.removeObject(forKey: bookmarkKey)
        resolvedURL = nil
        displayPath = "Not configured"
    }
}
