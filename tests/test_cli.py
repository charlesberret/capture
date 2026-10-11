"""CLI help and entry wiring. Offline; does not load the user's notes dir."""

from __future__ import annotations

import subprocess
import sys


def test_top_level_help_names_the_staging_folder():
    result = subprocess.run(
        [sys.executable, "-m", "capture.cli", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Process staging folder" in result.stdout
    assert "_Capture" not in result.stdout
