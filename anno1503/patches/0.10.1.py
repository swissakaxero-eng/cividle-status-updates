"""Anno 1503 Auto Trainer V0.10.1 remote-update smoke test.

Purpose: verify the permanent bootstrap end-to-end without a new manual ZIP.
No gameplay logic is changed. Only version markers/UI text are advanced and a
small marker file is added to the persistent source tree.
"""
from pathlib import Path

VERSION = "0.10.1"


def _replace_exact(path: Path, old: str, new: str, count: int | None = None):
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual == 0:
        raise RuntimeError(f"Expected text not found in {path.name}: {old!r}")
    if count is not None and actual != count:
        raise RuntimeError(
            f"Unexpected occurrence count in {path.name}: {old!r} -> {actual}, expected {count}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root):
    root = Path(root)

    core = root / "Anno1503_AutoTrainer.py"
    gui = root / "Anno1503_AutoTrainer_GUI.py"
    updater = root / "updater.py"
    for p in (core, gui, updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    # Core version constant and visible banner only. Gameplay logic is untouched.
    _replace_exact(core, 'TRAINER_VERSION = "0.10.0"', 'TRAINER_VERSION = "0.10.1"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.0',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.1',
        1,
    )

    # GUI-visible version labels + result metadata. Keep the bootstrap help text
    # that explicitly mentions the one-time V0.10.0 installation unchanged.
    _replace_exact(
        gui,
        'self.root.title("Anno 1503 Auto Trainer V0.10.0 PERMANENT BOOTSTRAP")',
        'self.root.title("Anno 1503 Auto Trainer V0.10.1 PERMANENT BOOTSTRAP")',
        1,
    )
    _replace_exact(
        gui,
        'text="Anno 1503 Auto Trainer V0.10.0 PERMANENT BOOTSTRAP"',
        'text="Anno 1503 Auto Trainer V0.10.1 PERMANENT BOOTSTRAP"',
        1,
    )
    _replace_exact(gui, '"version":"0.10.0"', '"version":"0.10.1"', 1)
    _replace_exact(
        gui,
        'self._set_status("V0.10.0: Warenlerner aus V0.9.5 unverändert; Speedpfad separat abgesichert …")',
        'self._set_status("V0.10.1: Bootstrap-Fernupdate aktiv; Warenlerner/Speedlogik unverändert …")',
        1,
    )

    # Updater must identify itself as the new installed trainer after rebuild.
    _replace_exact(updater, 'CURRENT_VERSION = "0.10.0"', 'CURRENT_VERSION = "0.10.1"', 1)

    (root / "REMOTE_UPDATE_SMOKETEST_V0_10_1.txt").write_text(
        "V0.10.1 installed by the permanent remote updater.\n"
        "Gameplay logic unchanged; this release verifies the no-more-manual-ZIP path.\n",
        encoding="utf-8",
    )
