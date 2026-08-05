import SwiftUI
import UniformTypeIdentifiers
import UIKit

struct SettingsView: View {
    @EnvironmentObject private var appModel: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var apiKey = KeychainService.googleAPIKey ?? ""
    @State private var showFolderPicker = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Notes folder") {
                    Text(appModel.notesStore.displayPath)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("Choose Folder") {
                        showFolderPicker = true
                    }
                    if appModel.notesStore.resolvedURL != nil {
                        Button("Clear", role: .destructive) {
                            appModel.notesStore.clearFolder()
                        }
                    }
                }

                Section("Gemini API") {
                    SecureField("Google API Key", text: $apiKey)
                        .textContentType(.password)
                        .autocorrectionDisabled()
                        #if os(iOS)
                        .textInputAutocapitalization(.never)
                        #endif
                    Text("Used for voice transcription, titles, and tags (gemini-2.0-flash).")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Providers") {
                    providerRow("Transcription", appModel.config.providerName(for: .transcription))
                    providerRow("OCR", appModel.config.providerName(for: .ocr))
                    providerRow("Title", appModel.config.providerName(for: .title))
                    providerRow("Tags", appModel.config.providerName(for: .tags))
                    providerRow("Correction", appModel.config.providerName(for: .correction))
                    providerRow("Connections", appModel.config.providerName(for: .connections))
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        KeychainService.googleAPIKey = apiKey
                        appModel.refreshPipeline()
                        dismiss()
                    }
                }
            }
            .sheet(isPresented: $showFolderPicker) {
                FolderPicker { url in
                    appModel.notesStore.setFolder(url)
                    showFolderPicker = false
                } onCancel: {
                    showFolderPicker = false
                }
            }
        }
    }

    private func providerRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
            Spacer()
            Text(value).foregroundStyle(.secondary)
        }
    }
}

struct FolderPicker: UIViewControllerRepresentable {
    let onPick: (URL) -> Void
    let onCancel: () -> Void

    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: [.folder])
        picker.delegate = context.coordinator
        picker.allowsMultipleSelection = false
        return picker
    }

    func updateUIViewController(_ uiViewController: UIDocumentPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onPick: onPick, onCancel: onCancel)
    }

    final class Coordinator: NSObject, UIDocumentPickerDelegate {
        let onPick: (URL) -> Void
        let onCancel: () -> Void

        init(onPick: @escaping (URL) -> Void, onCancel: @escaping () -> Void) {
            self.onPick = onPick
            self.onCancel = onCancel
        }

        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
            onCancel()
        }

        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            guard let url = urls.first else {
                onCancel()
                return
            }
            onPick(url)
        }
    }
}
