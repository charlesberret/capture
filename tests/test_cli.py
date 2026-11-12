"""CLI help and entry wiring. Offline; does not load the user's notes dir."""

from __future__ import annotations

import os
import subprocess
import sys

import yaml

from test_capture_floor import disabled_config


def test_top_level_help_names_the_staging_folder():
    result = subprocess.run(
        [sys.executable, "-m", "capture.cli", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Process staging folder" in result.stdout
    assert "_Capture" not in result.stdout


def test_dest_before_subcommand_writes_only_to_chosen(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    configured_notes = home / "configured-notes"
    configured_notes.mkdir()
    chosen = tmp_path / "chosen"
    chosen.mkdir()

    config_file = home / ".config" / "capture" / "config.yaml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(yaml.dump(disabled_config(configured_notes), sort_keys=False))

    env = {**os.environ, "HOME": str(home), "CAPTURE_CONFIG": str(config_file)}
    subprocess.run(
        [sys.executable, "-m", "capture.cli", "--dest", str(chosen), "quick", "hello"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    assert len(list(chosen.glob("*.md"))) == 1
    assert list(configured_notes.glob("*.md")) == []
    assert not (configured_notes / "_capture-staging").exists()
