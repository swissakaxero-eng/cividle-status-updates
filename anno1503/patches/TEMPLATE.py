"""Template for a future Anno 1503 trainer patch payload.

Copy to <version>.py, set VERSION, and implement apply(root).
The updater has already backed up the source tree before this runs.
"""
from pathlib import Path

VERSION = "0.10.1"

def apply(root):
    root = Path(root)
    # Example:
    # p = root / "some_file.py"
    # text = p.read_text(encoding="utf-8")
    # text = text.replace("old", "new")
    # p.write_text(text, encoding="utf-8")
    raise RuntimeError("Template only - do not publish this file in channel.json")
