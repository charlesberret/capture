"""Destination picker and path input helpers."""

from __future__ import annotations

import glob
import json
import os
import readline
import subprocess
from pathlib import Path

from capture.core.config import cfg

RECENT_DEST_FILE = Path.home() / ".cache/capture/recent-destinations.json"

_ICLOUD = str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs")
_HOME = str(Path.home())


def load_recent_destinations() -> list[str]:
    if RECENT_DEST_FILE.exists():
        try:
            return json.loads(RECENT_DEST_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_recent_destination(dest_path: Path) -> None:
    dest_str = str(dest_path)
    default_dir = Path(cfg()["notes_dir"]).expanduser()
    if dest_path == default_dir:
        return
    recents = load_recent_destinations()
    recents = [r for r in recents if r != dest_str]
    recents.insert(0, dest_str)
    recents = recents[: cfg()["ui"]["max_recent"]]
    RECENT_DEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECENT_DEST_FILE.write_text(json.dumps(recents, indent=2))


def shorten_path(p: Path | str) -> str:
    s = str(p)
    if s.startswith(_ICLOUD):
        return "iCloud" + s[len(_ICLOUD) :]
    if s.startswith(_HOME):
        return "~" + s[len(_HOME) :]
    return s


def _expand_capture_path(text: str) -> str:
    if text.startswith("iCloud/"):
        return _ICLOUD + text[len("iCloud") :]
    if text == "iCloud":
        return _ICLOUD + "/"
    return os.path.expanduser(text)


def _shorten_capture_path(abspath: str) -> str:
    if abspath.startswith(_ICLOUD + "/"):
        return "iCloud" + abspath[len(_ICLOUD) :]
    if abspath.startswith(_ICLOUD):
        return "iCloud" + abspath[len(_ICLOUD) :]
    if abspath.startswith(_HOME):
        return "~" + abspath[len(_HOME) :]
    return abspath


def _path_completer(text: str, state: int) -> str | None:
    if state == 0:
        _path_completer._matches = []
        if not text.startswith("iCloud/") and "iCloud/".startswith(text):
            _path_completer._matches.append("iCloud/")
        if not text.startswith("~/") and "~/".startswith(text) and text != "~":
            _path_completer._matches.append("~/")
        expanded = _expand_capture_path(text)
        for p in sorted(glob.glob(expanded + "*")):
            if os.path.isdir(p):
                short = _shorten_capture_path(p) + "/"
                if short not in _path_completer._matches:
                    _path_completer._matches.append(short)
    if state < len(_path_completer._matches):
        return _path_completer._matches[state]
    return None


_path_completer._matches = []


def input_path(prompt: str = "Path: ") -> str:
    old_completer = readline.get_completer()
    old_delims = readline.get_completer_delims()
    readline.set_completer(_path_completer)
    readline.set_completer_delims(" \t\n")
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    try:
        return input(prompt).strip().strip("'\"")
    finally:
        readline.set_completer(old_completer)
        readline.set_completer_delims(old_delims)


def resolve_dest_input(raw: str) -> Path | None:
    if not raw:
        return None
    raw = raw.rstrip("/")
    if raw.startswith("iCloud/") or raw == "iCloud":
        raw = str(
            Path.home()
            / "Library/Mobile Documents/com~apple~CloudDocs"
            / raw[len("iCloud/") :]
        )
    dest = Path(raw).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    save_recent_destination(dest)
    return dest


def choose_destination() -> Path:
    default_notes_dir = Path(cfg()["notes_dir"]).expanduser()
    recents = load_recent_destinations()
    default_display = shorten_path(default_notes_dir)

    options = [default_display]
    option_paths = [default_notes_dir]
    for r in recents:
        options.append(shorten_path(Path(r)))
        option_paths.append(Path(r))
    options.append("[new path]")

    try:
        fzf_input = "\n".join(options)
        result = subprocess.run(
            ["fzf", "--height=~10", "--layout=reverse", "--no-info", "--header=Save to:", "--pointer=▸"],
            input=fzf_input,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return default_notes_dir

        selection = result.stdout.strip()
        if selection == "[new path]":
            raw = input_path()
            dest = resolve_dest_input(raw)
            return dest if dest else default_notes_dir

        if selection in options:
            idx = options.index(selection)
            dest = option_paths[idx]
            if dest != default_notes_dir:
                save_recent_destination(dest)
            return dest
        return default_notes_dir

    except FileNotFoundError:
        print(f"\nSave to [{default_display}]:")
        for i, opt in enumerate(options[1:], 1):
            print(f"  {i}) {opt}")
        choice = input("\nEnter to accept, # to pick, or type a path: ").strip()
        if not choice:
            return default_notes_dir
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx < len(options):
                if options[idx] == "[new path]":
                    raw = input_path()
                    dest = resolve_dest_input(raw)
                    return dest if dest else default_notes_dir
                dest = option_paths[idx]
                if dest != default_notes_dir:
                    save_recent_destination(dest)
                return dest
        dest = resolve_dest_input(choice)
        return dest if dest else default_notes_dir
