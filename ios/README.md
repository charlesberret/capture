# Capture (iOS)

Native iOS app for multi-modal note capture. Writes the same timestamped `.md` kernel notes as the CLI, using Gemini Flash for transcription/titles/tags and Apple Vision for OCR.

## Requirements

- Xcode 16+
- iOS 17+
- Google API key (Gemini) — stored in Keychain

## Setup

```bash
cd ios
xcodegen generate
open Capture.xcodeproj
```

1. Set your **Development Team** in the Capture target (Signing & Capabilities).
2. Build and run on device or simulator.
3. In the app: **Settings → Choose Folder** — select your `Notes` folder (e.g. iCloud Drive/Notes).
4. **Settings → Google API Key** — paste your Gemini API key.

## Capture modes

| Mode | Extract | Enrich |
|------|---------|--------|
| Quick | Text input | Gemini title + tags |
| Text | Text editor | Gemini title + tags |
| Voice | Gemini Flash transcription | Gemini title + tags |
| Photo | Apple Vision OCR | Gemini title + tags |
| Scan | VisionKit scanner → Vision OCR | Gemini title + tags |

## Provider defaults

Mirrors `capture/platforms/ios.defaults.yaml`:

- `transcription` → `gemini_flash`
- `ocr` → `apple_vision`
- `title` / `tags` → `gemini_flash`
- `correction` → `disabled`
- `connections` → `keyword`

## Note format

Identical to the CLI — YAML frontmatter with `title`, `date`, `tags`, then body content. Files land directly in your chosen Notes folder (no staging step required).

## Project structure

```
ios/
├── project.yml
└── Capture/
    ├── Sources/
    │   ├── Core/           # Pipeline, note formatting, prompts
    │   ├── Providers/      # Gemini, Vision OCR, connections
    │   ├── Services/       # Keychain, notes folder, audio
    │   └── Views/          # SwiftUI capture screens
    ├── Resources/Prompts/  # Shared with Python CLI
    └── Supporting/
```
