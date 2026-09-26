"""Anno 1503 Auto Trainer V0.10.5 - robust targeted speed diagnostics.

This release does NOT loosen calibration pass thresholds and does NOT change goods,
money or other gameplay write logic. It improves only the independent speed-counter
measurement path:
- targeted confirmation uses a broader evidence-ranked shortlist,
- targeted windows are longer to reduce zero-rate windows,
- broad and targeted diagnostic evidence is preserved in result files,
- AutoShare summary exposes the key diagnostic counts directly.
"""
from pathlib import Path

VERSION = "0.10.5"


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

    # Version markers only outside the diagnostic changes below.
    _replace_exact(core, 'TRAINER_VERSION = "0.10.4"', 'TRAINER_VERSION = "0.10.5"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.4',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.5',
        1,
    )

    # Keep the evaluator/pass criteria untouched. Only improve which candidates
    # receive the longer targeted confirmation and retain enough evidence to
    # understand missing rate windows.
    _replace_exact(
        core,
        '        confirmation_duration=max(3.5,float(phase_duration))\n',
        '        confirmation_duration=max(5.0,float(phase_duration))\n',
        1,
    )

    old_select = '''            near=pre.get("nearest_calibration_candidates") or []
            # Rein diagnostische Vorauswahl aus 1x/2x/4x; keine 6x-Daten beteiligt.
            shortlist=[]
            for row in near[:24]:
                try:
                    score=float(row.get("calibration_score",999.0))
                    addr=int(str(row.get("address")),16)
                except Exception:
                    continue
                if score <= 1.25 and addr != int(speed_info['addr']):
                    shortlist.append(addr)
                if len(shortlist) >= 12:
                    break
            if not shortlist:
                for row in near[:8]:
                    try:
                        addr=int(str(row.get("address")),16)
                    except Exception:
                        continue
                    if addr != int(speed_info['addr']):
                        shortlist.append(addr)
'''
    new_select = '''            near=pre.get("nearest_calibration_candidates") or []
            # V0.10.5: keine Pass-Schwelle lockern. Fuer die gezielte Messung wird
            # lediglich breiter und nach vorhandener 1x/2x/4x-Evidenz sortiert.
            # So dominieren nicht wenige zufaellig gut aussehende, aber selten
            # aktualisierte Zaehler die Bestätigungsrunde.
            ranked=[]
            for pos,row in enumerate(near[:100]):
                try:
                    score=float(row.get("calibration_score",999.0))
                    addr=int(str(row.get("address")),16)
                except Exception:
                    continue
                if addr == int(speed_info['addr']):
                    continue
                s2=row.get("ratio_2x_vs_bracketed_1x_samples") or []
                s4=row.get("ratio_4x_vs_bracketed_1x_samples") or []
                bracket_count=len(s2)+len(s4)
                bracket_families=(1 if s2 else 0)+(1 if s4 else 0)
                activity=0
                for key in ("rate_1x_global","rate_2x_global","rate_4x_global"):
                    try:
                        if float(row.get(key,0.0)) > 0.0:
                            activity += 1
                    except Exception:
                        pass
                ranked.append((-bracket_families,-bracket_count,-activity,score,pos,addr))
            ranked.sort()
            shortlist=[item[-1] for item in ranked[:24]]
'''
    _replace_exact(core, old_select, new_select, 1)

    old_result_prefix = '''        evaluation=evaluate_calibrated_runs(calibration_for_final,six_runs)
        result={
            "version":TRAINER_VERSION,
'''
    new_result_prefix = '''        evaluation=evaluate_calibrated_runs(calibration_for_final,six_runs)

        # Compact, explicit evidence for the open rate_count=0 diagnosis.
        # Broad scan remains summarized; only the small targeted phase retains
        # per-address rates. No memory values are written here.
        broad_near=(pre.get("nearest_calibration_candidates") or [])[:40]
        targeted_activity=[]
        for addr in confirmation_addresses:
            present=[]
            values=[]
            for phase in confirmation_runs:
                rates=phase.get("rates") or {}
                rate=rates.get(addr)
                present.append(rate is not None)
                values.append(float(rate) if rate is not None else None)
            targeted_activity.append({
                "address":hex(int(addr)),
                "rate_present_by_phase":present,
                "rates_by_phase":values,
                "present_count":sum(1 for x in present if x),
                "phase_count":len(present),
            })

        result={
            "version":TRAINER_VERSION,
'''
    _replace_exact(core, old_result_prefix, new_result_prefix, 1)

    old_result_mid = '''            "targeted_confirmation_sequence":list(confirmation_sequence) if confirmation_used else [],
            "six_test_sequence":list(six_sequence),
'''
    new_result_mid = '''            "targeted_confirmation_sequence":list(confirmation_sequence) if confirmation_used else [],
            "broad_precheck":{
                "calibrated_count":pre.get("calibrated_count"),
                "median_ratio_2x_vs_1x":pre.get("median_ratio_2x_vs_1x"),
                "median_ratio_4x_vs_1x":pre.get("median_ratio_4x_vs_1x"),
                "nearest_calibration_candidates":broad_near,
            },
            "targeted_candidate_activity":targeted_activity,
            "six_test_sequence":list(six_sequence),
'''
    _replace_exact(core, old_result_mid, new_result_mid, 1)

    old_target_output = '''            "targeted_confirmation_phases":[{k:v for k,v in p.items() if k!="rates"} for p in confirmation_runs],
            "six_test_phases":[{k:v for k,v in p.items() if k!="rates"} for p in six_runs],
'''
    new_target_output = '''            "targeted_confirmation_phases":[{
                **{k:v for k,v in p.items() if k!="rates"},
                "rates":{hex(int(a)):float(r) for a,r in (p.get("rates") or {}).items()},
            } for p in confirmation_runs],
            "six_test_phases":[{k:v for k,v in p.items() if k!="rates"} for p in six_runs],
'''
    _replace_exact(core, old_target_output, new_target_output, 1)

    # AutoShare summary: keep the newest diagnostic visible without opening the ZIP.
    old_summary = '''        best = nearest[0] if nearest and isinstance(nearest[0], dict) else {}

        out["speed"] = {
'''
    new_summary = '''        best = nearest[0] if nearest and isinstance(nearest[0], dict) else {}
        broad = compare.get("broad_precheck") or {}
        broad_nearest = broad.get("nearest_calibration_candidates") or []
        broad_best = broad_nearest[0] if broad_nearest and isinstance(broad_nearest[0], dict) else {}
        targeted_phases = compare.get("targeted_confirmation_phases") or []

        out["speed"] = {
'''
    _replace_exact(share, old_summary, new_summary, 1)

    old_summary_tail = '''            "nearest_candidate": {
                "address": best.get("address"),
                "ratio_2x_vs_1x": best.get("ratio_2x_vs_1x"),
                "ratio_4x_vs_1x": best.get("ratio_4x_vs_1x"),
                "ratio_6x_vs_1x_median": best.get("ratio_6x_vs_1x_median"),
                "calibration_score": best.get("calibration_score"),
                "calibration_fail_reasons": best.get("calibration_fail_reasons") or [],
            },
        }
'''
    new_summary_tail = '''            "nearest_candidate": {
                "address": best.get("address"),
                "ratio_2x_vs_1x": best.get("ratio_2x_vs_1x"),
                "ratio_4x_vs_1x": best.get("ratio_4x_vs_1x"),
                "ratio_6x_vs_1x_median": best.get("ratio_6x_vs_1x_median"),
                "calibration_score": best.get("calibration_score"),
                "calibration_fail_reasons": best.get("calibration_fail_reasons") or [],
            },
            "broad_precheck_calibrated_count": broad.get("calibrated_count"),
            "broad_nearest_candidate": {
                "address": broad_best.get("address"),
                "ratio_2x_vs_1x": broad_best.get("ratio_2x_vs_1x"),
                "ratio_4x_vs_1x": broad_best.get("ratio_4x_vs_1x"),
                "calibration_score": broad_best.get("calibration_score"),
                "calibration_fail_reasons": broad_best.get("calibration_fail_reasons") or [],
            },
            "targeted_confirmation_used": bool(compare.get("targeted_confirmation_used")),
            "targeted_confirmation_candidate_count": compare.get("targeted_confirmation_candidate_count"),
            "targeted_confirmation_rate_counts": [
                p.get("rate_count") for p in targeted_phases if isinstance(p, dict)
            ],
        }
'''
    _replace_exact(share, old_summary_tail, new_summary_tail, 1)

    # Visible version markers.
    _replace_exact(
        gui,
        'Anno 1503 Auto Trainer V0.10.4 PERMANENT BOOTSTRAP',
        'Anno 1503 Auto Trainer V0.10.5 PERMANENT BOOTSTRAP',
        2,
    )
    _replace_exact(gui, '"version":"0.10.4"', '"version":"0.10.5"', 1)
    _replace_exact(
        gui,
        'V0.10.4: kompakte Bedienung; Update immer oben sichtbar …',
        'V0.10.5: Speed-Bestätigung robuster; Grenzwerte unverändert …',
        1,
    )
    _replace_exact(updater, 'CURRENT_VERSION = "0.10.4"', 'CURRENT_VERSION = "0.10.5"', 1)

    (root / "CHANGELOG_V0_10_5.md").write_text(
        "# V0.10.5\n\n"
        "- Keine Kalibrierungs-Grenzwerte gelockert.\n"
        "- Gezielte Bestätigung: bis zu 24 nach Evidenzabdeckung sortierte Kandidaten.\n"
        "- Gezielte Messfenster von mindestens 3.5s auf mindestens 5.0s verlängert.\n"
        "- Broad-Precheck und gezielte Per-Phase-Raten werden im Ergebnis erhalten.\n"
        "- AutoShare-Summary zeigt Kandidatenzahl und rate_count-Folge direkt.\n"
        "- Keine Änderung an Waren-, Geld- oder sonstiger Gameplay-Schreiblogik.\n",
        encoding="utf-8",
    )
