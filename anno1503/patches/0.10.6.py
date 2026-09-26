"""Anno 1503 Auto Trainer V0.10.6 - clean PyInstaller restart environment.

Fixes the post-update restart only. No speed thresholds, goods, money or gameplay
write logic is changed.

A frozen PyInstaller process can pass private _PYI_* runtime variables to the
external update worker. If the worker later starts the rebuilt EXE with those
stale values, the new EXE may try to reuse the old _MEI temp directory and fail
to load python314.dll after the old process has exited.
"""
from pathlib import Path
import os

VERSION = "0.10.6"


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


def _clean_current_worker_environment():
    # This runs inside the already-running update worker. Cleaning it here also
    # protects the restart at the END of this very update.
    for key in tuple(os.environ):
        if key.startswith("_PYI_") or key == "_MEIPASS2":
            os.environ.pop(key, None)
    os.environ["PYINSTALLER_RESET_ENVIRONMENT"] = "1"


def _patch_updater_restart_environment(path: Path):
    text = path.read_text(encoding="utf-8")
    marker = "V0106_PYINSTALLER_CLEAN_RESTART"
    if marker in text:
        return

    launch_anchor = "def launch_apply_script(script_path):"
    pos = text.find(launch_anchor)
    if pos < 0:
        raise RuntimeError("launch_apply_script not found in updater.py")

    helper = '''# V0106_PYINSTALLER_CLEAN_RESTART
def _clean_pyinstaller_child_env():
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("_PYI_") or key == "_MEIPASS2":
            env.pop(key, None)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


'''
    text = text[:pos] + helper + text[pos:]

    # Make the Python update worker independent from the frozen GUI's _MEI state.
    pos = text.find(launch_anchor)
    next_def = text.find("\ndef ", pos + len(launch_anchor))
    if next_def < 0:
        next_def = len(text)
    block = text[pos:next_def]
    if "env=_clean_pyinstaller_child_env()" not in block:
        needle = "            creationflags=flags,\n        )"
        if needle not in block:
            raise RuntimeError("launch_apply_script Popen block not recognized")
        block = block.replace(
            needle,
            "            creationflags=flags,\n"
            "            env=_clean_pyinstaller_child_env(),\n"
            "        )",
            1,
        )
        text = text[:pos] + block + text[next_def:]

    # Secondary defense for any future update worker started by another path.
    apply_pos = text.find("def _apply_plan(")
    if apply_pos < 0:
        raise RuntimeError("_apply_plan not found in updater.py")
    line_end = text.find("\n", apply_pos)
    if line_end < 0 or not text[apply_pos:line_end].rstrip().endswith(":"):
        raise RuntimeError("_apply_plan signature is not single-line as expected")
    injection = (
        "    # V0106_PYINSTALLER_CLEAN_RESTART: independent frozen restart\n"
        "    for _key in tuple(os.environ):\n"
        "        if _key.startswith(\"_PYI_\") or _key == \"_MEIPASS2\":\n"
        "            os.environ.pop(_key, None)\n"
        "    os.environ[\"PYINSTALLER_RESET_ENVIRONMENT\"] = \"1\"\n"
    )
    text = text[: line_end + 1] + injection + text[line_end + 1 :]
    path.write_text(text, encoding="utf-8")


def apply(root):
    _clean_current_worker_environment()

    root = Path(root)
    core = root / "Anno1503_AutoTrainer.py"
    gui = root / "Anno1503_AutoTrainer_GUI.py"
    updater = root / "updater.py"
    for p in (core, gui, updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    _replace_exact(core, 'TRAINER_VERSION = "0.10.5"', 'TRAINER_VERSION = "0.10.6"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.5',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.6',
        1,
    )

    _replace_exact(
        gui,
        'Anno 1503 Auto Trainer V0.10.5 PERMANENT BOOTSTRAP',
        'Anno 1503 Auto Trainer V0.10.6 PERMANENT BOOTSTRAP',
        2,
    )
    _replace_exact(gui, '"version":"0.10.5"', '"version":"0.10.6"', 1)
    _replace_exact(
        gui,
        'V0.10.5: Speed-Bestätigung robuster; Grenzwerte unverändert …',
        'V0.10.6: Update-Neustart repariert; Speed-/Spieltests unverändert …',
        1,
    )
    _replace_exact(updater, 'CURRENT_VERSION = "0.10.5"', 'CURRENT_VERSION = "0.10.6"', 1)
    _patch_updater_restart_environment(updater)

    (root / "CHANGELOG_V0_10_6.md").write_text(
        "# V0.10.6\n\n"
        "- Behebt den python314.dll/_MEI-Fehler beim automatischen Neustart nach Updates.\n"
        "- PyInstaller-private _PYI_* Variablen werden vor unabhängigen Neustarts entfernt.\n"
        "- PYINSTALLER_RESET_ENVIRONMENT=1 erzwingt eine frische _MEI-Umgebung.\n"
        "- Der bereits laufende Update-Worker wird während dieses Updates ebenfalls bereinigt.\n"
        "- Keine Änderung an Speed-Kalibrierungsgrenzen, Waren-, Geld- oder Gameplay-Schreiblogik.\n",
        encoding="utf-8",
    )
