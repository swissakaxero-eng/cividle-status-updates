"""Anno 1503 Auto Trainer V0.10.4 - compact update controls.

UI-only release: keeps the update status/button permanently in the upper visible
area and allows a shorter window. No gameplay, speed, goods, money or memory-write
logic is changed.
"""
from pathlib import Path

VERSION = "0.10.4"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.10.3"', 'TRAINER_VERSION = "0.10.4"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.3',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.4',
        1,
    )

    # Visible version markers.
    _replace_exact(
        gui,
        'Anno 1503 Auto Trainer V0.10.3 PERMANENT BOOTSTRAP',
        'Anno 1503 Auto Trainer V0.10.4 PERMANENT BOOTSTRAP',
        2,
    )
    _replace_exact(gui, '"version":"0.10.3"', '"version":"0.10.4"', 1)
    _replace_exact(
        gui,
        'V0.10.3: gezielte Speed-Bestätigung aktiv; Warenlerner/Schreiblogik unverändert …',
        'V0.10.4: kompakte Bedienung; Update immer oben sichtbar …',
        1,
    )
    _replace_exact(updater, 'CURRENT_VERSION = "0.10.3"', 'CURRENT_VERSION = "0.10.4"', 1)

    # Allow the trainer window to be used at a much smaller height.
    _replace_exact(gui, 'self.root.minsize(880, 640)', 'self.root.minsize(820, 420)', 1)

    # Put updater controls directly under the title/subtitle so they remain visible
    # even when the lower half of the trainer window is not on screen.
    top_anchor = '''        ttk.Label(top, text="Speed-Sicherheitsbasis + belastbarere Kalibrierung + AutoShare + permanenter Auto-Updater",
                  font=("Segoe UI", 9)).pack(anchor="w", pady=(2,0))
'''
    top_new = top_anchor + '''
        # V0.10.4: Update controls stay permanently in the upper visible area.
        update_top = ttk.Frame(top)
        update_top.pack(fill="x", pady=(6,0))
        ttk.Label(update_top, textvariable=self.update_status_var).pack(side="left", fill="x", expand=True)
        self.update_btn = ttk.Button(update_top, text="Update prüfen", command=self.update_button_clicked)
        self.update_btn.pack(side="right", padx=(8,0))
'''
    _replace_exact(gui, top_anchor, top_new, 1)

    # Keep the lower legal/safety note, but remove the duplicated updater controls.
    bottom_old = '''        self.update_btn = ttk.Button(bottom, text="Update prüfen", command=self.update_button_clicked)
        self.update_btn.pack(side="right", padx=(8,0))
        ttk.Label(bottom, textvariable=self.update_status_var).pack(side="right")
'''
    _replace_exact(gui, bottom_old, '', 1)

    (root / "CHANGELOG_V0_10_4.md").write_text(
        "# V0.10.4\n\n"
        "- Update prüfen + Update-Status dauerhaft oben sichtbar.\n"
        "- Mindestfensterhöhe von 640 auf 420 reduziert.\n"
        "- Keine Änderung an Speed-, Waren-, Geld- oder Speicherwrite-Logik.\n",
        encoding="utf-8",
    )
