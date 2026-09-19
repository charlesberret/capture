# Capture (iOS)

Native iOS app for multi-modal note capture — **the phone path**. Writes the
same timestamped `.md` kernel notes as the CLI, directly to your chosen Notes
folder (no staging step). Supersedes the legacy iOS-Shortcuts staging flow
documented in the root README; this app is the product path.

## The photo loop: highlight-confirm-memo

The agent never writes behind your back. For a photographed page:

1. **Photograph** a print or handwritten page (camera or VisionKit scanner).
2. **See the OCR** — Apple Vision text is displayed to you first; nothing is
   stored yet.
3. **Highlight** the span that becomes the note body. Saving without a
   selection is refused.
4. The **agent proposes title + tags** (Gemini Flash). You confirm — edits
   allowed — and may add a short memo, which appends to the body.
5. Only then is the note written, in the same `YYYYMMDDHHMM - Title.md`
   shape the CLI writes, with the same YAML frontmatter.

Text and voice modes follow the same gate: agent proposes, human confirms,
then the note is written.

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

| Mode | Extract | Enrich | Write gate |
|------|---------|--------|-------------|
| Quick | Text input | Gemini title + tags | confirm |
| Text | Text editor | Gemini title + tags | confirm |
| Voice | Gemini Flash transcription | Gemini title + tags | confirm |
| Photo | Apple Vision OCR (shown) | Gemini title + tags | highlight + confirm |
| Scan | VisionKit scanner → Vision OCR (shown) | Gemini title + tags | highlight + confirm |

## Provider defaults

Mirrors `capture/platforms/ios.defaults.yaml`:

- `transcription` → `gemini_flash`
- `ocr` → `apple_vision`
- `title` / `tags` → `gemini_flash`
- `correction` → `disabled`
- `connections` → `keyword`

Without a Gemini key the app still works in degrade mode: titles fall back to
first-line truncation, tags are skipped — the confirm gate and note shape are
unchanged.

## Note format

Identical to the CLI — YAML frontmatter with `title`, `date`, `tags`, then
body content. Files land directly in your chosen Notes folder.

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
