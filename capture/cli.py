#!/usr/bin/env python3
"""capture CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from capture.core import state
from capture.core.fragments import DEFAULT_THRESHOLD
from capture.core.config import DEFAULT_CONFIG_TEMPLATE, load_config, set_config
from capture.core.pipeline import (
    capture_photo,
    capture_quick,
    capture_text,
    capture_voice,
    capture_voice_multi,
    process_capture_folder,
)
from capture.core.ui import choose_destination, save_recent_destination, shorten_path


def interactive_menu() -> None:
    dest_display = shorten_path(state.NOTES_DIR)
    print(f"""
╔═══════════════════════════════════╗
║         CAPTURE                   ║
╠═══════════════════════════════════╣
║  [q] Quick one-liner              ║
║  [t] Text block (editor)          ║
║  [p] Photo/image (OCR)            ║
║  [v] Voice recording              ║
║  [r] Process _Capture folder      ║
║  [x] Exit                         ║
╚═══════════════════════════════════╝
  → {dest_display}
""")

    choice = input("Select: ").strip().lower()

    if choice == "q":
        print("Enter idea (one line):")
        text = input().strip()
        if text:
            capture_quick(text)
    elif choice == "t":
        capture_text()
    elif choice == "p":
        capture_photo()
    elif choice == "v":
        capture_voice()
    elif choice == "r":
        process_capture_folder()
    elif choice == "x":
        print("Bye")
    else:
        print("Unknown option")


def run_fragments(threshold: int | None = None, write: bool = False) -> None:
    from capture.core import fragments as frag

    threshold = threshold or frag.DEFAULT_THRESHOLD
    notes_dir = state.NOTES_DIR
    found = frag.scan(notes_dir, threshold=threshold)

    if not found:
        print(f"No fragments under {threshold} chars in {shorten_path(notes_dir)}")
        return

    print(f"\n{len(found)} fragment{'s' if len(found) != 1 else ''} "
          f"under {threshold} chars in {shorten_path(notes_dir)}:\n")
    for f in found:
        mark = "EMPTY" if f.is_empty else f"{f.chars:4}c/{f.words:3}w"
        print(f"  [{mark}] {f.title[:58]}")

    path = frag.desk_path(notes_dir)
    result = frag.reconcile(frag.load_queue(path), found, notes_dir, threshold)

    print(f"\nDesk: {shorten_path(path)}")
    print(f"  new items to file : {len(result['added'])}")
    print(f"  already settled   : {len(result['skipped'])} (left alone)")
    print(f"  now resolved      : {len(result['resolved'])} (note grew past the bar)")

    if not write:
        print("\nReport only — pass --write to file them.")
        return

    frag.write_queue(path, result["queue"])
    print(f"\n\u2713 Filed {len(result['added'])} item"
          f"{'s' if len(result['added']) != 1 else ''} on the desk")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick idea capture tool")
    parser.add_argument("--dest", "-d", type=str, help="Destination directory (default: Notes/)")
    parser.add_argument("--config", type=str, metavar="PATH", help="Path to config file")
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Generate default config at ~/.config/capture/config.yaml",
    )
    subparsers = parser.add_subparsers(dest="command")

    quick_parser = subparsers.add_parser("quick", help="One-liner capture")
    quick_parser.add_argument("--dest", "-d", type=str, help=argparse.SUPPRESS)
    quick_parser.add_argument("text", nargs="+", help="Text to capture")

    text_parser = subparsers.add_parser("text", help="Open editor for text capture")
    text_parser.add_argument("--dest", "-d", type=str, help=argparse.SUPPRESS)

    photo_parser = subparsers.add_parser("photo", help="OCR from image")
    photo_parser.add_argument("--dest", "-d", type=str, help=argparse.SUPPRESS)
    photo_parser.add_argument("file", nargs="?", help="Image file path")

    voice_parser = subparsers.add_parser("voice", help="Record and transcribe voice")
    voice_parser.add_argument("--dest", "-d", type=str, help=argparse.SUPPRESS)
    voice_parser.add_argument(
        "--multi", "-m", action="store_true", help="Record multiple notes with pipelined transcription"
    )
    voice_parser.add_argument(
        "--topic", "-t", type=str, default="general", help="Topic for vocabulary hints (default: general)"
    )
    voice_parser.add_argument(
        "--no-correct", action="store_true", help="Skip post-transcription correction pass"
    )

    fragments_parser = subparsers.add_parser(
        "fragments", help="Find notes too short to be useful and file them on the Kettle desk"
    )
    fragments_parser.add_argument("--dest", "-d", type=str, help=argparse.SUPPRESS)
    fragments_parser.add_argument(
        "--threshold", type=int, default=None, metavar="CHARS",
        help=f"Body length below which a note counts as a fragment "
             f"(default: {DEFAULT_THRESHOLD})",
    )
    fragments_parser.add_argument(
        "--write", action="store_true",
        help="File the entries on the desk (default: report only)",
    )

    process_parser = subparsers.add_parser("process", help="Process _Capture folder")
    process_parser.add_argument("--dest", "-d", type=str, help=argparse.SUPPRESS)
    process_parser.add_argument(
        "--topic", "-t", type=str, default="general", help="Topic for vocabulary hints (default: general)"
    )
    process_parser.add_argument(
        "--no-correct", action="store_true", help="Skip post-transcription correction pass"
    )

    args = parser.parse_args()

    if args.init_config:
        config_dir = Path.home() / ".config" / "capture"
        config_file = config_dir / "config.yaml"
        if config_file.exists():
            print(f"Config already exists: {config_file}")
            print("Delete it first if you want to regenerate.")
            sys.exit(1)
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(DEFAULT_CONFIG_TEMPLATE)
        print(f"Created: {config_file}")
        sys.exit(0)

    if args.config:
        set_config(load_config(args.config))
    else:
        set_config(load_config())

    from capture.core.config import cfg

    default_notes_dir = Path(cfg()["notes_dir"]).expanduser()
    dest = args.dest
    if dest:
        state.NOTES_DIR = Path(dest).expanduser().resolve()
    elif args.command:
        state.NOTES_DIR = default_notes_dir
    else:
        state.NOTES_DIR = choose_destination()

    state.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    capture_dir = Path(cfg()["capture_dir"]).expanduser()
    capture_dir.mkdir(parents=True, exist_ok=True)

    if state.NOTES_DIR != default_notes_dir:
        save_recent_destination(state.NOTES_DIR)

    if args.command == "quick":
        capture_quick(" ".join(args.text))
    elif args.command == "text":
        capture_text()
    elif args.command == "photo":
        capture_photo(args.file)
    elif args.command == "voice":
        topic = getattr(args, "topic", "general")
        correct = not getattr(args, "no_correct", False)
        if args.multi:
            capture_voice_multi(topic=topic, correct=correct)
        else:
            capture_voice(topic=topic, correct=correct)
    elif args.command == "fragments":
        run_fragments(threshold=args.threshold, write=args.write)
    elif args.command == "process":
        topic = getattr(args, "topic", "general")
        correct = not getattr(args, "no_correct", False)
        process_capture_folder(topic=topic, correct=correct)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
