"""Anno 1503 Auto Trainer V0.11.11 - UI cleanup after diagnostics.

Hides obsolete experimental test buttons from the normal GUI while preserving
their code internally for recovery/diagnostics. Keeps productive turbo controls
and original safe baseline controls visible.
"""
from pathlib import Path

VERSION = "0.11.11"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.11.10"', 'TRAINER_VERSION = "0.11.11"', 1)

    g = gui.read_text(encoding="utf-8")

    anchor = '''        self.turbostop_btn = ttk.Button(
            stress_actions, text="TURBO STOP", command=self.stop_turbo_best, state="disabled"
        )
        self.turbostop_btn.pack(side="left", padx=8)
'''
    if anchor not in g:
        raise RuntimeError("Turbo button anchor not found")

    cleanup = anchor + '''        # V01111_UI_CLEANUP
        # Alte Diagnose-/Experiment-Buttons bleiben intern erhalten, werden aber
        # aus der normalen Bedienoberflaeche entfernt.
        for _name in (
            "speed16_btn",
            "speedstress_btn",
            "effectivespeed_btn",
            "limiterab_btn",
            "cpurender_btn",
            "miniturbo_btn",
        ):
            _widget = getattr(self, _name, None)
            if _widget is not None:
                try:
                    _widget.pack_forget()
                except Exception:
                    pass
        try:
            for _widget in list(stress_actions.winfo_children()):
                try:
                    if isinstance(_widget, ttk.Label) and "stoppt automatisch" in str(_widget.cget("text")):
                        _widget.pack_forget()
                except Exception:
                    pass
        except Exception:
            pass
'''
    g = g.replace(anchor, cleanup, 1)
    gui.write_text(g, encoding="utf-8")

    _replace_exact(updater, 'CURRENT_VERSION = "0.11.10"', 'CURRENT_VERSION = "0.11.11"', 1)

    (root / "CHANGELOG_V0_11_11.md").write_text(
        "# V0.11.11 - UI Cleanup\n\n"
        "- Alte experimentelle Testbuttons aus der normalen EXE-Oberflaeche ausgeblendet.\n"
        "- Intern bleibt die Diagnose-Logik fuer Recovery/gezielte spaetere Tests erhalten.\n"
        "- Sichtbar bleiben die produktiven Turbo-Funktionen und die sicheren Grundfunktionen.\n"
        "- Keine Aenderung an Speed-, Geld-, Waren-, Speicherwrite- oder Updater-Logik.\n",
        encoding="utf-8",
    )
