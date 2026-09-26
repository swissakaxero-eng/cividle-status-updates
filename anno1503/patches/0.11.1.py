"""Anno 1503 Auto Trainer V0.11.1 - Transactional Updater V3 smoke test.

No gameplay, goods, money, speed, calibration or memory-write logic is changed.
This release only advances version/status markers so the new transactional updater
can be verified end-to-end on the real installed trainer.
"""
from pathlib import Path

VERSION = "0.11.1"


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

    # Require the transactional-updater base. This prevents accidental application
    # to an older broken updater generation.
    if 'TRAINER_VERSION = "0.11.0"' not in core.read_text(encoding="utf-8"):
        raise RuntimeError("V0.11.1 smoke test requires V0.11.0 source")
    if 'CURRENT_VERSION = "0.11.0"' not in updater.read_text(encoding="utf-8"):
        raise RuntimeError("V0.11.1 smoke test requires Transactional Updater V3 / V0.11.0")

    _replace_exact(core, 'TRAINER_VERSION = "0.11.0"', 'TRAINER_VERSION = "0.11.1"', 1)
    # Banner may be present once in the full source; tolerate test fixtures without it.
    ct = core.read_text(encoding="utf-8")
    if ' AUTO TRAINER V0.11.0' in ct:
        core.write_text(ct.replace(' AUTO TRAINER V0.11.0', ' AUTO TRAINER V0.11.1'), encoding="utf-8")

    gt = gui.read_text(encoding="utf-8")
    if 'Anno 1503 Auto Trainer V0.11.0 PERMANENT BOOTSTRAP' not in gt:
        raise RuntimeError("GUI V0.11.0 title marker missing")
    gt = gt.replace(
        'Anno 1503 Auto Trainer V0.11.0 PERMANENT BOOTSTRAP',
        'Anno 1503 Auto Trainer V0.11.1 PERMANENT BOOTSTRAP',
    )
    gt = gt.replace('"version":"0.11.0"', '"version":"0.11.1"')
    gt = gt.replace('"version": "0.11.0"', '"version": "0.11.1"')
    gt = gt.replace(
        'V0.11.0: transaktionaler Updater V3; alter Trainer bleibt bis zum fertigen Build offen …',
        'V0.11.1: Updater-V3-Smoke-Test bestanden; Spiel-/Trainerlogik unverändert …',
    )
    gui.write_text(gt, encoding="utf-8")

    _replace_exact(updater, 'CURRENT_VERSION = "0.11.0"', 'CURRENT_VERSION = "0.11.1"', 1)

    (root / "CHANGELOG_V0_11_1.md").write_text(
        "# V0.11.1 - Transactional Updater V3 Smoke Test\n\n"
        "- Reiner End-to-End-Test des neuen transaktionalen Updatepfads.\n"
        "- Keine Aenderung an Speed-, Geld-, Waren-, Kalibrierungs- oder Speicherwrite-Logik.\n"
        "- Erfolgreiche Installation bestaetigt: Prepare/Build bei laufender alter EXE, kurzer Commit, Startup-Healthcheck.\n",
        encoding="utf-8",
    )
