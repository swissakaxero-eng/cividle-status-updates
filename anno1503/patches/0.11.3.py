"""Anno 1503 Auto Trainer V0.11.3 - updater V3.1 silent smoke test.

Pure updater smoke release. No gameplay, speed, money, goods, calibration,
or process-memory test logic is changed.
"""
from pathlib import Path

VERSION = "0.11.3"


def _replace_exact(path: Path, old: str, new: str, count: int | None = None):
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual == 0:
        raise RuntimeError(f"Expected text not found in {path.name}: {old!r}")
    if count is not None and actual != count:
        raise RuntimeError(f"Unexpected occurrence count in {path.name}: {actual} != {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root):
    root = Path(root)
    core = root / "Anno1503_AutoTrainer.py"
    gui = root / "Anno1503_AutoTrainer_GUI.py"
    updater = root / "updater.py"
    for p in (core, gui, updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    _replace_exact(core, 'TRAINER_VERSION = "0.11.2"', 'TRAINER_VERSION = "0.11.3"', 1)
    ct = core.read_text(encoding="utf-8")
    if ' AUTO TRAINER V0.11.2' in ct:
        core.write_text(ct.replace(' AUTO TRAINER V0.11.2', ' AUTO TRAINER V0.11.3'), encoding="utf-8")

    gt = gui.read_text(encoding="utf-8")
    if 'Anno 1503 Auto Trainer V0.11.2 PERMANENT BOOTSTRAP' not in gt:
        raise RuntimeError("V0.11.2 GUI title marker not found")
    gt = gt.replace(
        'Anno 1503 Auto Trainer V0.11.2 PERMANENT BOOTSTRAP',
        'Anno 1503 Auto Trainer V0.11.3 PERMANENT BOOTSTRAP'
    )
    gt = gt.replace('"version":"0.11.2"', '"version":"0.11.3"')
    gt = gt.replace('"version": "0.11.2"', '"version": "0.11.3"')
    gt = gt.replace(
        'V0.11.2: Updater V3.1; Build-Helfer unsichtbar + Fortschritt gespiegelt …',
        'V0.11.3: V3.1 Silent-Smoke-Test; Spiel-/Trainerlogik unverändert …'
    )
    gui.write_text(gt, encoding="utf-8")

    _replace_exact(updater, 'CURRENT_VERSION = "0.11.2"', 'CURRENT_VERSION = "0.11.3"', 1)

    (root / "CHANGELOG_V0_11_3.md").write_text(
        "# V0.11.3 - V3.1 Silent Smoke Test\n\n"
        "- Reiner End-to-End-Test des Transactional Updater V3.1 Silent.\n"
        "- Keine Aenderung an Speed-, Geld-, Waren-, Kalibrierungs- oder Gameplay-Logik.\n"
        "- Erwartung: alter Trainer bleibt bis zum fertigen Build offen; Helper bleiben unsichtbar; kurzer Commit + Healthcheck.\n",
        encoding="utf-8",
    )
