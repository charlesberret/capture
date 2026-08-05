import SwiftUI

struct CaptureResultView: View {
    let result: CaptureResult

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Saved", systemImage: "checkmark.circle.fill")
                .foregroundStyle(.green)
                .font(.headline)

            Text(result.title)
                .font(.title3)

            Text(result.filename)
                .font(.caption)
                .foregroundStyle(.secondary)

            if !result.tags.isEmpty {
                Text(result.tags.joined(separator: " "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if !result.connections.isEmpty {
                Label("Related: \(result.connections.joined(separator: ", "))", systemImage: "link")
                    .font(.caption)
            }

            if let serendipity = result.serendipity {
                Text(serendipity)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 12))
    }
}
