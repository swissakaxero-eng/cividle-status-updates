"""Anno 1503 Auto Trainer V0.10.2 - AutoShare summary update.

No gameplay, memory-write or speed-control logic is changed. This release adds
a compact machine-readable LATEST_RESULT_SUMMARY.json next to the mirrored ZIP
so ChatGPT can inspect the newest run quickly after OneDrive synchronization.
"""
from pathlib import Path

VERSION = "0.10.2"


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
    share = root / "result_share.py"
    for p in (core, gui, updater, share):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    # Version markers only; gameplay logic remains untouched.
    _replace_exact(core, 'TRAINER_VERSION = "0.10.1"', 'TRAINER_VERSION = "0.10.2"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.1',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.2',
        1,
    )
    _replace_exact(
        gui,
        'self.root.title("Anno 1503 Auto Trainer V0.10.1 PERMANENT BOOTSTRAP")',
        'self.root.title("Anno 1503 Auto Trainer V0.10.2 PERMANENT BOOTSTRAP")',
        1,
    )
    _replace_exact(
        gui,
        'text="Anno 1503 Auto Trainer V0.10.1 PERMANENT BOOTSTRAP"',
        'text="Anno 1503 Auto Trainer V0.10.2 PERMANENT BOOTSTRAP"',
        1,
    )
    _replace_exact(gui, '"version":"0.10.1"', '"version":"0.10.2"', 1)
    _replace_exact(
        gui,
        'self._set_status("V0.10.1: Bootstrap-Fernupdate aktiv; Warenlerner/Speedlogik unverändert …")',
        'self._set_status("V0.10.2: AutoShare-Summary aktiv; Warenlerner/Speedlogik unverändert …")',
        1,
    )
    _replace_exact(
        gui,
        'self.result_sync_var.set("Auto-Share: OneDrive ✓ — LATEST_RESULT.zip gespiegelt")',
        'self.result_sync_var.set("Auto-Share: OneDrive ✓ — ZIP + Summary gespiegelt")',
        1,
    )
    _replace_exact(updater, 'CURRENT_VERSION = "0.10.1"', 'CURRENT_VERSION = "0.10.2"', 1)

    st = share.read_text(encoding="utf-8")
    marker = "V0102_RESULT_SUMMARY"
    if marker not in st:
        # Add imports needed by the compact summary extractor.
        if "import hashlib\n" not in st:
            st = st.replace("import json\n", "import json\nimport hashlib\nimport zipfile\n", 1)

        anchor = "\ndef mirror_result_to_sync(path):\n"
        if st.count(anchor) != 1:
            raise RuntimeError("result_share mirror function anchor not unique")

        helper = '''
# V0102_RESULT_SUMMARY
def _sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _zip_json(zf, name):
    try:
        with zf.open(name, "r") as f:
            return json.loads(f.read().decode("utf-8"))
    except Exception:
        return None


def build_result_summary(path):
    """Return a compact, path-free summary of one finished result ZIP."""
    src = Path(path).resolve()
    if not src.is_file():
        raise FileNotFoundError(str(src))

    out = {
        "schema": 1,
        "project": "Anno 1503 Auto Trainer",
        "kind": "latest_result_summary",
        "result_zip": src.name,
        "result_zip_size": src.stat().st_size,
        "result_zip_sha256": _sha256_file(src),
        "summary_created_unix": time.time(),
    }

    with zipfile.ZipFile(src, "r") as zf:
        names = set(zf.namelist())
        out["result_files"] = sorted(names)

        learning = _zip_json(zf, "speed_learning_diagnostics.json") or {}
        restore = _zip_json(zf, "speed_restore_diagnostics.json") or {}
        compare = _zip_json(zf, "speed_compare_1x_2x_4x_calibrated_6x.json") or {}

        run_version = compare.get("version") or learning.get("version")
        if run_version:
            out["run_version"] = run_version

        binding = compare.get("binding") or {}
        resets = compare.get("phase_resets_to_1x") or []
        nearest = compare.get("nearest_calibration_candidates") or []
        best = nearest[0] if nearest and isinstance(nearest[0], dict) else {}

        out["speed"] = {
            "binding_verified": bool(binding.get("verified")),
            "binding_address": binding.get("address"),
            "binding_readback": binding.get("f5_readback"),
            "restore_verified": bool(restore.get("verified")),
            "restore_readback": restore.get("readback"),
            "phase_reset_total": len(resets),
            "phase_reset_verified": sum(1 for x in resets if isinstance(x, dict) and x.get("verified")),
            "calibrated_count": compare.get("calibrated_count"),
            "stable_6x_count": compare.get("stable_6x_count"),
            "median_ratio_2x_vs_1x": compare.get("median_ratio_2x_vs_1x"),
            "median_ratio_4x_vs_1x": compare.get("median_ratio_4x_vs_1x"),
            "median_ratio_6x_vs_1x_all_calibrated": compare.get("median_ratio_6x_vs_1x_all_calibrated"),
            "median_ratio_6x_vs_1x_stable": compare.get("median_ratio_6x_vs_1x_stable"),
            "nearest_candidate": {
                "address": best.get("address"),
                "ratio_2x_vs_1x": best.get("ratio_2x_vs_1x"),
                "ratio_4x_vs_1x": best.get("ratio_4x_vs_1x"),
                "ratio_6x_vs_1x_median": best.get("ratio_6x_vs_1x_median"),
                "calibration_score": best.get("calibration_score"),
                "calibration_fail_reasons": best.get("calibration_fail_reasons") or [],
            },
        }
    return out


'''
        st = st.replace(anchor, "\n" + helper + "def mirror_result_to_sync(path):\n", 1)

        old = '''    (destdir/"LATEST_RESULT.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding="utf-8")
    return {"mirrored":True,**meta}
'''
        new = '''    (destdir/"LATEST_RESULT.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding="utf-8")
    try:
        summary = build_result_summary(src)
        summary_path = destdir / "LATEST_RESULT_SUMMARY.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        meta["summary"] = str(summary_path)
        meta["summary_sha256"] = summary.get("result_zip_sha256")
    except Exception as exc:
        # ZIP sharing must never fail merely because optional summary extraction failed.
        meta["summary_error"] = str(exc)
    return {"mirrored":True,**meta}
'''
        if st.count(old) != 1:
            raise RuntimeError("result_share final mirror block not unique")
        st = st.replace(old, new, 1)
        share.write_text(st, encoding="utf-8")

    (root / "CHANGELOG_V0_10_2.md").write_text(
        "# V0.10.2\n\n"
        "- AutoShare erzeugt LATEST_RESULT_SUMMARY.json neben LATEST_RESULT.zip.\n"
        "- Summary enthält ZIP-SHA256, Restore-/Reset-Status und kompakte Speed-Messwerte.\n"
        "- Keine Änderung an Spiel-, Speicherwrite-, Waren-, Geld- oder Speed-Steuerlogik.\n",
        encoding="utf-8",
    )
