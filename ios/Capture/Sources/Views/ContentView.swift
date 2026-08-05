import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var selectedMode: CaptureMode?
    @State private var showSettings = false
    @State private var showResult = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                if appModel.notesStore.resolvedURL == nil {
                    Section {
                        Label("Choose your Notes folder in Settings", systemImage: "folder.badge.questionmark")
                            .foregroundStyle(.orange)
                    }
                }

                Section("Capture") {
                    ForEach(CaptureMode.allCases) { mode in
                        Button {
                            selectedMode = mode
                        } label: {
                            Label {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(mode.title)
                                    Text(mode.subtitle)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            } icon: {
                                Image(systemName: mode.systemImage)
                                    .foregroundStyle(.tint)
                            }
                        }
                    }
                }

                if let result = appModel.lastResult {
                    Section("Last capture") {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(result.title).font(.headline)
                            Text(result.filename).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle("Capture")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showSettings = true
                    } label: {
                        Image(systemName: "gearshape")
                    }
                }
            }
            .overlay {
                if appModel.isProcessing {
                    ProgressView(appModel.statusMessage ?? "Working…")
                        .padding()
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
            }
            .sheet(item: $selectedMode) { mode in
                captureSheet(for: mode)
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
            }
            .alert("Capture Error", isPresented: Binding(
                get: { errorMessage != nil },
                set: { if !$0 { errorMessage = nil } }
            )) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }

    @ViewBuilder
    private func captureSheet(for mode: CaptureMode) -> some View {
        NavigationStack {
            Group {
                switch mode {
                case .quick:
                    QuickCaptureView { text in
                        try await appModel.captureText(text)
                    }
                case .text:
                    TextCaptureView { text in
                        try await appModel.captureText(text)
                    }
                case .voice:
                    VoiceCaptureView { url in
                        try await appModel.captureVoice(from: url)
                    }
                case .photo:
                    PhotoCaptureView { url in
                        try await appModel.captureImage(at: url)
                    }
                case .scan:
                    ScanCaptureView { url in
                        try await appModel.captureScan(at: url)
                    }
                }
            }
            .environmentObject(appModel)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { selectedMode = nil }
                }
            }
        }
    }
}
