"""Pipeline orchestration for extract → refine → enrich stages."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path

from capture.core.config import cfg, get_stage_provider_name
from capture.core.note import create_note
from capture.core.vocabulary import (
    build_whisper_prompt,
    flatten_vocabulary,
    load_whisper_dictionary,
)
from capture.providers.registry import get_provider


def warmup_enrich() -> object | None:
    """Warm up the title provider if it supports background warmup."""
    provider = get_provider("title")
    warmup = getattr(provider, "warmup", None)
    if callable(warmup):
        return warmup()
    return None


def transcribe_audio(
    audio_path: Path | str,
    topic: str = "general",
    *,
    correct: bool = True,
    source: str = "audio",
) -> str | None:
    """Extract text from audio, then optionally run the correction stage."""
    audio_path = Path(audio_path)
    vocab_by_topic, corrections, templates = load_whisper_dictionary()
    hints = {
        "topic": topic,
        "vocab_by_topic": vocab_by_topic,
        "templates": templates,
        "corrections": corrections,
    }

    provider = get_provider("transcription")
    text = provider.transcribe(audio_path, hints=hints)

    if not text:
        return None

    if correct and get_stage_provider_name("correction") != "disabled":
        refine = get_provider("correction")
        vocabulary = ", ".join(flatten_vocabulary(vocab_by_topic))
        refined = refine.correct(text, source=source, vocabulary=vocabulary)
        if refined:
            text = refined

    return text


def transcribe_async(audio_path: Path | str, topic: str = "general", *, correct: bool = True):
    """Start transcription in a background thread."""
    result_holder: list[str | None] = [None]

    def _do():
        result_holder[0] = transcribe_audio(audio_path, topic=topic, correct=correct)

    thread = threading.Thread(target=_do)
    thread.start()
    return thread, result_holder, Path(audio_path)


def ocr_image(filepath: Path | str) -> str | None:
    provider = get_provider("ocr")
    text = provider.extract(Path(filepath))
    if text:
        return text
    # Fallback chain: try other OCR providers if primary failed
    config = cfg()
    primary = config["providers"]["ocr"]["default"]
    for name, _ in config["providers"]["ocr"].items():
        if name in ("default", primary, "disabled"):
            continue
        fallback = get_provider("ocr", provider_name=name)
        text = fallback.extract(Path(filepath))
        if text:
            return text
    return None


def ocr_pdf(filepath: Path | str) -> str | None:
    from capture.providers.ocr.apple_vision import ocr_pdf as vision_pdf

    return vision_pdf(Path(filepath))


def _find_local_mic() -> str:
    try:
        result = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = result.stderr.splitlines()
        in_audio = False
        for line in lines:
            if "audio devices" in line.lower():
                in_audio = True
                continue
            if in_audio and "[" in line:
                m = re.search(r"\[(\d+)\]\s+(.+)", line)
                if m:
                    idx, name = m.group(1), m.group(2)
                    if "MacBook" in name or "Built-in" in name:
                        return idx
    except Exception:
        pass
    return "0"


def start_recording() -> tuple[subprocess.Popen, str]:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_audio = f.name

    try:
        proc = subprocess.Popen(["rec", "-q", temp_audio], stdin=subprocess.PIPE)
    except FileNotFoundError:
        mic_idx = _find_local_mic()
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-f",
                "avfoundation",
                "-i",
                f":{mic_idx}",
                "-y",
                "-loglevel",
                "quiet",
                temp_audio,
            ],
            stdin=subprocess.PIPE,
        )
    return proc, temp_audio


def capture_quick(text: str) -> Path:
    warmup = warmup_enrich()
    return create_note(text, warmup=warmup)


def capture_text() -> Path | None:
    warmup = warmup_enrich()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Capture\n\n")
        temp_path = f.name

    subprocess.run([cfg()["editor"], temp_path])
    content = Path(temp_path).read_text().strip()
    os.unlink(temp_path)

    if content == "# Capture" or not content:
        print("Capture cancelled (empty)")
        return None
    if content.startswith("# Capture\n"):
        content = content[len("# Capture\n") :].strip()
    return create_note(content, warmup=warmup)


def _confirm_or_edit(text: str) -> str | None:
    print(f"\n--- Preview ---\n{text}\n---")
    print("\nOptions: [s]ave as-is, [e]dit first, [c]ancel")
    choice = input().strip().lower()
    if choice == "c":
        print("Cancelled")
        return None
    if choice == "e":
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(text)
            temp_path = f.name
        subprocess.run([cfg()["editor"], temp_path])
        text = Path(temp_path).read_text().strip()
        os.unlink(temp_path)
    return text


def capture_photo(filepath: Path | str | None = None) -> Path | None:
    if filepath is None:
        print("Enter path to image (or drag file here):")
        filepath = input().strip().strip("'\"")
    filepath = Path(filepath).expanduser()
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        raise SystemExit(1)

    text = ocr_image(filepath)
    if not text:
        print("Error: Could not extract text from image")
        raise SystemExit(1)

    text = _confirm_or_edit(text)
    if text is None:
        return None
    return create_note(text)


def capture_voice(topic: str = "general", correct: bool = True) -> Path | None:
    print("Recording... Press Enter to stop.")
    rec_proc, temp_audio = start_recording()
    input()
    rec_proc.terminate()
    rec_proc.wait()

    print("Transcribing...")
    text = transcribe_audio(temp_audio, topic=topic, correct=correct)
    os.unlink(temp_audio)

    if not text:
        print("Error: Transcription failed")
        return None

    text = _confirm_or_edit(text)
    if text is None:
        return None
    return create_note(text)


def capture_voice_multi(topic: str = "general", correct: bool = True) -> None:
    note_num = 0
    created = [0]
    filing_thread = None

    def _file_async(audio_path: str, num: int) -> None:
        text = transcribe_audio(audio_path, topic=topic, correct=correct)
        os.unlink(audio_path)
        if text:
            create_note(text)
            created[0] += 1
            print(f"  Note {num} filed: {len(text)} chars")
        else:
            print(f"  Note {num} failed.")

    print("Multi-capture mode. Press Enter to stop each recording.")
    print("Type 'q' + Enter to finish the session.\n")

    while True:
        note_num += 1
        print(f"--- Note {note_num} ---")
        print("Recording... (Enter to stop, 'q' to finish)")
        rec_proc, temp_audio = start_recording()
        user_input = input().strip().lower()
        rec_proc.terminate()
        rec_proc.wait()

        if user_input == "q":
            os.unlink(temp_audio)
            break

        if filing_thread:
            filing_thread.join()
            filing_thread = None

        print(f"  Transcribing note {note_num} in background...")
        filing_thread = threading.Thread(target=_file_async, args=(temp_audio, note_num))
        filing_thread.start()

    if filing_thread:
        print("Processing final note...")
        filing_thread.join()

    print(f"\n{'='*40}")
    print(f"Session complete: {created[0]} note{'s' if created[0] != 1 else ''} created")
    print(f"{'='*40}")


def process_capture_folder(topic: str = "general", correct: bool = True) -> None:
    from capture.core.note import create_note as write_note

    capture_dir = Path(cfg()["capture_dir"]).expanduser()
    if not capture_dir.exists():
        print(f"Capture folder not found: {capture_dir}")
        return

    items = [
        item
        for item in capture_dir.iterdir()
        if item.is_file() and item.name not in ("README.md", ".DS_Store")
    ]
    if not items:
        print("No items to process")
        return

    print(f"Processing {len(items)} item{'s' if len(items) != 1 else ''}...\n")
    processed = {"text": 0, "photo": 0, "pdf": 0, "voice": 0, "skipped": 0}

    for idx, item in enumerate(items, 1):
        print(f"[{idx}/{len(items)}] {item.name}")

        if item.suffix.lower() in (".txt", ".md"):
            content = item.read_text().strip()
            if content:
                write_note(content)
                processed["text"] += 1
            item.unlink()

        elif item.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic"):
            print("  → OCR processing...")
            text = ocr_image(item)
            if text:
                print(f"  ✓ Extracted {len(text)} chars")
                write_note(text)
                processed["photo"] += 1
            else:
                print("  ✗ Could not OCR image")
                processed["skipped"] += 1
            item.unlink()

        elif item.suffix.lower() == ".pdf":
            print("  → OCR processing PDF...")
            text = ocr_pdf(item)
            if text:
                print(f"  ✓ Extracted {len(text)} chars")
                write_note(text)
                processed["pdf"] += 1
            else:
                print("  ✗ Could not OCR PDF")
                processed["skipped"] += 1
            item.unlink()

        elif item.suffix.lower() in (".m4a", ".mp3", ".wav", ".caf"):
            print("  → Transcribing...")
            try:
                text = transcribe_audio(item, topic=topic, correct=correct)
                if text:
                    print(f"  ✓ Transcribed {len(text)} chars")
                    write_note(text)
                    processed["voice"] += 1
                else:
                    print("  ✗ Transcription failed")
                    processed["skipped"] += 1
            except Exception as e:
                print(f"  ✗ Error: {e}")
                processed["skipped"] += 1
            item.unlink()
        else:
            print(f"  → Skipping unknown type: {item.suffix}")
            processed["skipped"] += 1

    print(f"\n{'='*40}")
    print("Processing complete!")
    total = sum(processed.values())
    created = total - processed.get("skipped", 0)
    if total > 0:
        for typ, count in processed.items():
            if count > 0:
                emoji = {"text": "📝", "photo": "📷", "pdf": "📄", "voice": "🎤", "skipped": "⊘"}[typ]
                print(f"  {emoji} {typ.title()}: {count}")
    print(f"{'='*40}")

    if created > 0:
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "Created {created} note{"s" if created != 1 else ""}" '
                    f'with title "Capture" sound name "Glass"',
                ],
                capture_output=True,
            )
        except Exception:
            pass
