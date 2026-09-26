"""Anno 1503 Auto Trainer V0.10.3 - targeted speed confirmation.

No goods/money write logic is changed. The speed comparison becomes two-stage:
first a broad 1x/2x/4x scan, then (only when needed) a long targeted repeated
1x/2x/4x confirmation on the best few candidates. 6x is still measured only
after candidate selection and never influences that selection.
"""
from pathlib import Path

VERSION = "0.10.3"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.10.2"', 'TRAINER_VERSION = "0.10.3"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.2',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.3',
        1,
    )

    old = '''        # Auch bei wenigen Treffern Diagnose fahren; nur wenn wirklich keiner kalibriert,
        # wird 6x nicht als objektiv messbar behauptet.
        for idx,factor in enumerate(six_sequence,1):
            _raise_if_stopped(stop_event, "6x-Messung")
            print(f"[SPEED-KALIBRIERUNG] Prüfphase {idx}/{len(six_sequence)}: {factor:g}x …")
            reset,phase=_run_calibration_phase(
                hproc,hwnd,speed_info,addresses,factor,phase_duration,
                stop_event=stop_event,expected_pid=expected_pid
            )
            phase_resets.append({"group":"six_test","index":idx,"before_factor":factor,**reset})
            six_runs.append(phase)

        evaluation=evaluate_calibrated_runs(calibration_runs,six_runs)
        result={
            "version":TRAINER_VERSION,
            "method":"bracketed_standard_calibrated_independent_u32_rates",
            "selection_rule":"Kandidaten ausschließlich über lokale 1x-2x-1x und 1x-4x-1x Klammern; 6x beeinflusst die Auswahl nicht.",
            "timing_rule":"Jede Adresse nutzt eigenen Start-/Endzeitpunkt; vor der Messung 0.25s Einschwingzeit; 2x/4x werden gegen benachbarte 1x-Fenster normiert.",
            "binding":binding,
            "discovery":{
                "snapshot_bytes":total,
                "elapsed_sec":discover_elapsed,
                "candidate_count":len(addresses),
            },
            "phase_duration_sec":float(phase_duration),
            "calibration_sequence":list(calibration_sequence),
            "six_test_sequence":list(six_sequence),
            "phase_resets_to_1x":phase_resets,
            "same_loaded_game_state":True,
            "exact_save_reload_between_phases":False,
            "standard_phases":[{k:v for k,v in p.items() if k!="rates"} for p in calibration_runs],
            "six_test_phases":[{k:v for k,v in p.items() if k!="rates"} for p in six_runs],
            **evaluation,
        }
'''
    new = '''        # V0.10.3: Wenn der breite 8000-Adressen-Scan nur wegen fehlender
        # Wiederholungen keinen Kandidaten freigibt, werden die besten Kandidaten
        # gezielt und länger erneut mit 1x/2x/4x bestätigt. Die Auswahl bleibt
        # ausschließlich 1x/2x/4x-basiert; 6x darf sie weiterhin nicht beeinflussen.
        confirmation_runs=[]
        confirmation_sequence=(1.0,2.0,1.0,2.0,1.0,4.0,1.0,4.0,1.0)
        confirmation_duration=max(3.5,float(phase_duration))
        confirmation_addresses=[]
        confirmation_used=False
        calibration_for_final=calibration_runs
        pre_for_final=pre

        if pre.get("calibrated_count",0) == 0:
            near=pre.get("nearest_calibration_candidates") or []
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

            # Deduplizieren, Reihenfolge beibehalten.
            seen=set()
            confirmation_addresses=[]
            for addr in shortlist:
                if addr not in seen:
                    seen.add(addr)
                    confirmation_addresses.append(addr)

            if confirmation_addresses:
                confirmation_used=True
                print(
                    f"[SPEED-KALIBRIERUNG] Gezielte Bestätigung: {len(confirmation_addresses)} Kandidaten, "
                    f"{confirmation_duration:.1f}s je Phase."
                )
                for idx,factor in enumerate(confirmation_sequence,1):
                    _raise_if_stopped(stop_event, "Gezielte Standardbestätigung")
                    print(
                        f"[SPEED-KALIBRIERUNG] Bestätigungsphase {idx}/{len(confirmation_sequence)}: "
                        f"{factor:g}x …"
                    )
                    reset,phase=_run_calibration_phase(
                        hproc,hwnd,speed_info,confirmation_addresses,factor,confirmation_duration,
                        stop_event=stop_event,expected_pid=expected_pid
                    )
                    phase_resets.append({
                        "group":"targeted_confirmation","index":idx,
                        "before_factor":factor,**reset
                    })
                    confirmation_runs.append(phase)

                confirm_eval=evaluate_calibrated_runs(confirmation_runs,[])
                print(
                    f"[SPEED-KALIBRIERUNG] Gezielte Bestätigung: "
                    f"kalibriert={confirm_eval['calibrated_count']} | "
                    f"2x/1x={confirm_eval['median_ratio_2x_vs_1x']} | "
                    f"4x/1x={confirm_eval['median_ratio_4x_vs_1x']}"
                )
                calibration_for_final=confirmation_runs
                pre_for_final=confirm_eval

        # 6x wird nur auf den 1x/2x/4x-bestätigten Adressen geprüft. Falls weiterhin
        # kein Kandidat bestätigt wurde, werden höchstens die gezielten Adressen nur
        # diagnostisch gemessen; daraus entsteht keine positive 6x-Freigabe.
        selected_for_six=[]
        for row in pre_for_final.get("calibrated_candidates") or []:
            try:
                selected_for_six.append(int(str(row.get("address")),16))
            except Exception:
                pass
        if not selected_for_six:
            selected_for_six=list(confirmation_addresses[:12]) if confirmation_addresses else list(addresses[:32])
        selected_for_six=list(dict.fromkeys(selected_for_six))[:32]
        six_duration=max(3.5,float(phase_duration))

        print(
            f"[SPEED-KALIBRIERUNG] 6x-Prüfung auf {len(selected_for_six)} gezielten Kandidaten, "
            f"{six_duration:.1f}s je Phase."
        )
        for idx,factor in enumerate(six_sequence,1):
            _raise_if_stopped(stop_event, "6x-Messung")
            print(f"[SPEED-KALIBRIERUNG] Prüfphase {idx}/{len(six_sequence)}: {factor:g}x …")
            reset,phase=_run_calibration_phase(
                hproc,hwnd,speed_info,selected_for_six,factor,six_duration,
                stop_event=stop_event,expected_pid=expected_pid
            )
            phase_resets.append({"group":"six_test","index":idx,"before_factor":factor,**reset})
            six_runs.append(phase)

        evaluation=evaluate_calibrated_runs(calibration_for_final,six_runs)
        result={
            "version":TRAINER_VERSION,
            "method":"two_stage_bracketed_standard_then_targeted_confirmation_u32_rates",
            "selection_rule":"Kandidaten ausschließlich über 1x/2x/4x; bei Bedarf gezielte Wiederholungsbestätigung. 6x beeinflusst die Auswahl nicht.",
            "timing_rule":"Breitscan mit adressgenauen Zeitfenstern; bei fehlender Wiederholung gezielte 3.5s+-Bestätigung; 6x danach nur auf bestätigten Kandidaten.",
            "binding":binding,
            "discovery":{
                "snapshot_bytes":total,
                "elapsed_sec":discover_elapsed,
                "candidate_count":len(addresses),
            },
            "phase_duration_sec":float(phase_duration),
            "calibration_sequence":list(calibration_sequence),
            "targeted_confirmation_used":confirmation_used,
            "targeted_confirmation_duration_sec":confirmation_duration if confirmation_used else None,
            "targeted_confirmation_candidate_count":len(confirmation_addresses),
            "targeted_confirmation_sequence":list(confirmation_sequence) if confirmation_used else [],
            "six_test_sequence":list(six_sequence),
            "six_test_duration_sec":six_duration,
            "six_test_candidate_count":len(selected_for_six),
            "phase_resets_to_1x":phase_resets,
            "same_loaded_game_state":True,
            "exact_save_reload_between_phases":False,
            "standard_phases":[{k:v for k,v in p.items() if k!="rates"} for p in calibration_runs],
            "targeted_confirmation_phases":[{k:v for k,v in p.items() if k!="rates"} for p in confirmation_runs],
            "six_test_phases":[{k:v for k,v in p.items() if k!="rates"} for p in six_runs],
            **evaluation,
        }
'''
    _replace_exact(core, old, new, 1)

    _replace_exact(
        gui,
        'Anno 1503 Auto Trainer V0.10.2 PERMANENT BOOTSTRAP',
        'Anno 1503 Auto Trainer V0.10.3 PERMANENT BOOTSTRAP',
        2,
    )
    _replace_exact(gui, '"version":"0.10.2"', '"version":"0.10.3"', 1)
    _replace_exact(
        gui,
        'V0.10.2: AutoShare-Summary aktiv; Warenlerner/Speedlogik unverändert …',
        'V0.10.3: gezielte Speed-Bestätigung aktiv; Warenlerner/Schreiblogik unverändert …',
        1,
    )
    _replace_exact(updater, 'CURRENT_VERSION = "0.10.2"', 'CURRENT_VERSION = "0.10.3"', 1)

    (root / "CHANGELOG_V0_10_3.md").write_text(
        "# V0.10.3\n\n"
        "- Zweistufige Speed-Messung: Breitscan plus gezielte Wiederholungsbestätigung.\n"
        "- 6x erst nach 1x/2x/4x-Auswahl; 6x beeinflusst die Kandidatenauswahl nicht.\n"
        "- Gezielte 6x-Prüfung nur auf wenigen bestätigten Kandidaten mit längeren Fenstern.\n"
        "- Keine Änderung an Waren-, Geld- oder sonstiger Schreiblogik.\n",
        encoding="utf-8",
    )
