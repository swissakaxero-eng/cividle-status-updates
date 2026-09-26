"""Anno 1503 Auto Trainer V0.10.10 - offline-guided fast measurements + robust money pulses.

Does not loosen the existing speed calibration pass thresholds. Uses previous
completed result data offline to select shorter live measurement windows, with one
longer retry only if evidence is too sparse. The Ctrl+M money learner is also made
robust against delayed processing/missed pulses. No blind money writes.
"""
from pathlib import Path

VERSION = "0.10.10"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.10.9"', 'TRAINER_VERSION = "0.10.10"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.9',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.10',
        1,
    )

    # Robust money confirmation: keep the proven first broad +500 discovery, but
    # poll the small candidate set after later Ctrl+M pulses so an asynchronous
    # game update is not mistaken for a failed candidate. The accepted window is
    # intentionally narrow and no direct money write is performed.
    money_anchor = '''def read_f32(hproc, addr):
'''
    if "def learn_money_robust(" not in core.read_text(encoding="utf-8"):
        money_helper = r'''def learn_money_robust(hproc, hwnd, required_hits=3, max_pulses=4, poll_timeout=0.45,
                       tolerance=20):
    """Robuste Variante der bestehenden 3x-STRG+M/+500-Geldsuche.

    Der erste Vollscan bleibt exakt +500. Danach werden nur diese wenigen
    Kandidaten unmittelbar nach jedem weiteren Ctrl+M mehrfach gelesen. Ein
    Treffer muss wiederholt nahe +500 liegen; es gibt weiterhin keinen direkten
    Geld-Speicherwrite.
    """
    print("\n[GELD V0.10.10] robuste Geldsuche startet.")
    focus_game(hwnd)
    before,total=snapshot_regions(hproc)
    chord(VK_CONTROL,VK_M)
    time.sleep(0.20)
    cand=set(diff_plus_32(before,hproc,500))
    print(f"  Kandidaten nach erstem exakten +500: {len(cand)}")
    diag={
        "version":TRAINER_VERSION,
        "method":"ctrl_m_first_exact_then_polled_near500",
        "memory_bytes_scanned":total,
        "required_hits":int(required_hits),
        "max_pulses":int(max_pulses),
        "poll_timeout_sec":float(poll_timeout),
        "tolerance":int(tolerance),
        "rounds":[],
        "initial_candidates":[hex(a) for a in sorted(cand)],
        "found":False,
        "address":None,
        "final_value":None,
        "direct_memory_write_used":False,
    }
    hits={a:1 for a in cand}
    pulse=1

    while cand and pulse < int(max_pulses):
        pulse += 1
        prev={a:read_i32(hproc,a) for a in cand}
        focus_game(hwnd)
        chord(VK_CONTROL,VK_M)
        started=time.monotonic()
        best={}
        accepted=set()
        accepted_delta={}
        while time.monotonic()-started < float(poll_timeout):
            for a,oldv in prev.items():
                if oldv is None:
                    continue
                now=read_i32(hproc,a)
                if now is None:
                    continue
                delta=int(now)-int(oldv)
                err=abs(delta-500)
                old_best=best.get(a)
                if old_best is None or err < old_best[0]:
                    best[a]=(err,delta,now,round(time.monotonic()-started,4))
                if err <= int(tolerance):
                    accepted.add(a)
                    accepted_delta[a]=delta
            if accepted:
                break
            time.sleep(0.04)

        row={
            "pulse":pulse,
            "candidate_count_before":len(cand),
            "accepted_count":len(accepted),
            "accepted":[hex(a) for a in sorted(accepted)],
            "accepted_deltas":{hex(a):accepted_delta[a] for a in sorted(accepted)},
            "best_observed":{
                hex(a):{
                    "delta":v[1],"error_from_500":v[0],"value":v[2],"t_sec":v[3]
                } for a,v in sorted(best.items())
            },
        }
        diag["rounds"].append(row)

        if accepted:
            cand=accepted
            for a in cand:
                hits[a]=hits.get(a,0)+1
            print(f"  Puls {pulse}: {len(cand)} Kandidat(en) nahe +500 bestätigt.")
        else:
            # Kein Treffer wird blind verworfen, wenn die Taste offenbar noch
            # nicht verarbeitet wurde. Wir behalten den kleinen Satz für den
            # naechsten Puls und dokumentieren die besten beobachteten Deltas.
            print(f"  Puls {pulse}: noch kein +500-Fenster getroffen; Kandidaten bleiben für Retry erhalten.")

        qualified=[a for a in cand if hits.get(a,0) >= int(required_hits)]
        if len(qualified)==1:
            addr=qualified[0]
            final=read_i32(hproc,addr)
            diag.update({"found":True,"address":hex(addr),"final_value":final,
                         "hits":hits.get(addr,0)})
            print(f"  [OK] Geldadresse robust bestätigt: 0x{addr:X}, aktueller Wert={final}")
            try:
                if RUN_DIR:
                    (RUN_DIR/"money_learning_robust.json").write_text(
                        json.dumps(diag,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
            except Exception:
                traceback.print_exc()
            return addr

    diag["remaining_candidates"]=[hex(a) for a in sorted(cand)]
    diag["hit_counts"]={hex(a):hits.get(a,0) for a in sorted(hits)}
    print(f"  [INFO] Geldadresse nach robustem Test nicht eindeutig: {len(cand)} verbleibend.")
    try:
        if RUN_DIR:
            (RUN_DIR/"money_learning_robust.json").write_text(
                json.dumps(diag,indent=2,ensure_ascii=False),encoding="utf-8"
            )
    except Exception:
        traceback.print_exc()
    return None


'''
        _replace_exact(core, money_anchor, money_helper + money_anchor, 1)

    # Offline/no-graphics pretest: read previous result data only. Old memory
    # addresses are never reused; only the duration profile is learned. This lets
    # repeated algorithm iterations happen without launching/rendering the game.
    compare_anchor = "def compare_speed_1x_4x_6x(hproc, hwnd, speed_info, stop_event=None, expected_pid=None,\n"
    if "def offline_speed_history_hint(" not in core.read_text(encoding="utf-8"):
        offline_helper = r'''def offline_speed_history_hint():
    out={
        "available":False,
        "mode":"conservative",
        "source_run":None,
        "targeted_rate_counts":[],
        "targeted_rate_count_median":None,
        "targeted_positive_fraction":None,
        "broad_duration_sec":1.20,
        "targeted_duration_sec":1.60,
        "six_duration_sec":1.50,
    }
    try:
        runs=sorted(
            [p for p in get_results_dir().glob("RUN_*") if p.is_dir()],
            key=lambda p:p.stat().st_mtime, reverse=True
        )
        for run in runs:
            fp=run/"speed_compare_1x_2x_4x_calibrated_6x.json"
            if not fp.is_file():
                continue
            data=json.loads(fp.read_text(encoding="utf-8"))
            phases=data.get("targeted_confirmation_phases") or []
            counts=[]
            for phase in phases:
                try:
                    counts.append(int(phase.get("rate_count") or 0))
                except Exception:
                    counts.append(0)
            if not counts:
                continue
            med=float(statistics.median(counts))
            frac=sum(1 for x in counts if x>0)/len(counts)
            out.update({
                "available":True,
                "source_run":run.name,
                "targeted_rate_counts":counts,
                "targeted_rate_count_median":med,
                "targeted_positive_fraction":frac,
            })
            if med >= 8.0 and frac >= 0.95:
                out.update({
                    "mode":"fast_history_supported",
                    "broad_duration_sec":0.90,
                    "targeted_duration_sec":1.25,
                    "six_duration_sec":1.20,
                })
            break
    except Exception as exc:
        out["error"]=f"{type(exc).__name__}: {exc}"
    try:
        if RUN_DIR:
            (RUN_DIR/"offline_speed_history_hint.json").write_text(
                json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8"
            )
    except Exception:
        pass
    return out


'''
        _replace_exact(core, compare_anchor, offline_helper + compare_anchor, 1)

    # Make the existing live comparison adaptive instead of creating a second
    # divergent evaluator. Existing thresholds/selection logic stay untouched.
    compare_text=core.read_text(encoding="utf-8")
    old_bind='''    binding=verify_speed_binding_with_f5(hproc, hwnd, speed_info, expected_pid=expected_pid)
    print(f"[SPEED-KALIBRIERUNG] Speed-Bindung bestätigt: {binding['address']} -> F5 Readback {binding['f5_readback']}")
    try:
'''
    new_bind='''    binding=verify_speed_binding_with_f5(hproc, hwnd, speed_info, expected_pid=expected_pid)
    offline_hint=offline_speed_history_hint()
    phase_duration=min(float(phase_duration),float(offline_hint.get("broad_duration_sec",phase_duration)))
    print(f"[SPEED-KALIBRIERUNG] Speed-Bindung bestätigt: {binding['address']} -> F5 Readback {binding['f5_readback']}")
    print(
        f"[SPEED-OFFLINE] {offline_hint.get('mode')} | Breitscan {phase_duration:.2f}s | "
        f"Ziel {float(offline_hint.get('targeted_duration_sec',1.6)):.2f}s | "
        f"6x {float(offline_hint.get('six_duration_sec',1.5)):.2f}s"
    )
    try:
'''
    if old_bind not in compare_text:
        raise RuntimeError("Speed binding anchor for offline timing not found")
    compare_text=compare_text.replace(old_bind,new_bind,1)
    compare_text=compare_text.replace(
        '        confirmation_duration=max(5.0,float(phase_duration))\n',
        '        confirmation_duration=max(float(offline_hint.get("targeted_duration_sec",1.60)),float(phase_duration))\n',
        1,
    )
    compare_text=compare_text.replace(
        '        confirmation_used=False\n        calibration_for_final=calibration_runs\n',
        '        confirmation_used=False\n        targeted_retry_used=False\n        calibration_for_final=calibration_runs\n',
        1,
    )
    retry_anchor='''                confirm_eval=evaluate_calibrated_runs(confirmation_runs,[])
'''
    retry_block='''                rate_counts=[int(p.get("rate_count") or 0) for p in confirmation_runs]
                positive=sum(1 for x in rate_counts if x>0)
                median_count=float(statistics.median(rate_counts)) if rate_counts else 0.0
                if confirmation_duration < 2.9 and (positive < 8 or median_count < 5.0):
                    targeted_retry_used=True
                    retry_duration=3.0
                    print(
                        f"[SPEED-OFFLINE] Kurzmessung zu dünn (median={median_count}, positive={positive}/9); "
                        f"einmaliger Ziel-Retry mit {retry_duration:.1f}s."
                    )
                    confirmation_runs=[]
                    for ridx,rfactor in enumerate(confirmation_sequence,1):
                        _raise_if_stopped(stop_event, "Gezielte Standardbestätigung Retry")
                        reset,phase=_run_calibration_phase(
                            hproc,hwnd,speed_info,confirmation_addresses,rfactor,retry_duration,
                            stop_event=stop_event,expected_pid=expected_pid
                        )
                        phase_resets.append({
                            "group":"targeted_confirmation_retry","index":ridx,
                            "before_factor":rfactor,**reset
                        })
                        confirmation_runs.append(phase)
                    confirmation_duration=retry_duration

                confirm_eval=evaluate_calibrated_runs(confirmation_runs,[])
'''
    if retry_anchor not in compare_text:
        raise RuntimeError("Targeted confirm evaluator anchor not found")
    compare_text=compare_text.replace(retry_anchor,retry_block,1)
    compare_text=compare_text.replace(
        '        six_duration=max(3.5,float(phase_duration))\n',
        '        six_duration=max(float(offline_hint.get("six_duration_sec",1.50)),float(phase_duration))\n',
        1,
    )
    compare_text=compare_text.replace(
        '            "targeted_confirmation_used":confirmation_used,\n',
        '            "offline_history_hint":offline_hint,\n            "targeted_confirmation_used":confirmation_used,\n            "targeted_retry_used":targeted_retry_used,\n',
        1,
    )
    core.write_text(compare_text,encoding="utf-8")

    # Separate empirical evidence layer. Existing evaluate_calibrated_runs pass
    # criteria remain untouched. This reports repeatability/monotonicity of the
    # actual 1x/2x/4x response so the next decision can be data-driven.
    speed_anchor = '''def set_standard_speed(hwnd):
'''
    if "def analyze_empirical_speed_response(" not in core.read_text(encoding="utf-8"):
        speed_helper = r'''def analyze_empirical_speed_response(compare_result):
    phases=(compare_result or {}).get("targeted_confirmation_phases") or []
    by_addr={}
    for phase in phases:
        try:
            factor=float(phase.get("factor"))
        except Exception:
            continue
        if factor not in (1.0,2.0,4.0):
            continue
        for addr,rate in (phase.get("rates") or {}).items():
            try:
                rv=float(rate)
            except Exception:
                continue
            if not math.isfinite(rv) or rv <= 0:
                continue
            by_addr.setdefault(str(addr),{1.0:[],2.0:[],4.0:[]})[factor].append(rv)

    def relspread(vals):
        if len(vals)<2:
            return None
        med=statistics.median(vals)
        if not med:
            return None
        return (max(vals)-min(vals))/abs(med)

    rows=[]
    for addr,g in by_addr.items():
        if not (g[1.0] and g[2.0] and g[4.0]):
            continue
        m1=statistics.median(g[1.0]); m2=statistics.median(g[2.0]); m4=statistics.median(g[4.0])
        r2=m2/m1 if m1 else None
        r4=m4/m1 if m1 else None
        s1=relspread(g[1.0]); s2=relspread(g[2.0]); s4=relspread(g[4.0])
        complete=(len(g[1.0])>=3 and len(g[2.0])>=2 and len(g[4.0])>=2)
        stable=complete and all(x is not None and x <= 0.20 for x in (s1,s2,s4))
        monotonic=bool(r2 is not None and r4 is not None and r2>1.05 and r4>r2*1.05)
        separation=(abs((r2 or 1)-1)+abs((r4 or 1)-(r2 or 1)))
        rows.append({
            "address":addr,
            "samples_1x":len(g[1.0]),"samples_2x":len(g[2.0]),"samples_4x":len(g[4.0]),
            "median_rate_1x":m1,"median_rate_2x":m2,"median_rate_4x":m4,
            "ratio_2x_vs_1x":r2,"ratio_4x_vs_1x":r4,
            "spread_1x":s1,"spread_2x":s2,"spread_4x":s4,
            "complete_repeats":complete,"stable_within_factor":stable,
            "monotonic_response":monotonic,"separation_score":separation,
        })
    rows.sort(key=lambda x:(
        not x["stable_within_factor"], not x["monotonic_response"],
        not x["complete_repeats"],
        (x["spread_1x"] if x["spread_1x"] is not None else 999)+
        (x["spread_2x"] if x["spread_2x"] is not None else 999)+
        (x["spread_4x"] if x["spread_4x"] is not None else 999),
        -x["separation_score"], x["address"]
    ))
    out={
        "version":TRAINER_VERSION,
        "kind":"empirical_standard_speed_response",
        "note":"Nur Zusatzdiagnose; bestehende Speed-Pass-Grenzen wurden nicht gelockert.",
        "candidate_count_with_all_factors":len(rows),
        "complete_repeat_count":sum(1 for x in rows if x["complete_repeats"]),
        "stable_within_factor_count":sum(1 for x in rows if x["stable_within_factor"]),
        "stable_monotonic_count":sum(1 for x in rows if x["stable_within_factor"] and x["monotonic_response"]),
        "candidates":rows[:80],
    }
    try:
        if RUN_DIR:
            (RUN_DIR/"speed_empirical_diagnostics.json").write_text(
                json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8"
            )
    except Exception:
        traceback.print_exc()
    return out


'''
        _replace_exact(core, speed_anchor, speed_helper + speed_anchor, 1)

    g=gui.read_text(encoding="utf-8")
    if "Anno 1503 Auto Trainer V0.10.9 PERMANENT BOOTSTRAP" not in g:
        raise RuntimeError("GUI 0.10.9 title marker not found")
    g=g.replace("Anno 1503 Auto Trainer V0.10.9 PERMANENT BOOTSTRAP",
                "Anno 1503 Auto Trainer V0.10.10 PERMANENT BOOTSTRAP")
    g=g.replace('"version":"0.10.9"','"version":"0.10.10"')
    g=g.replace("V0.10.9: sicherer Staging-Updater + Speed/Geld-Kombitest …",
                "V0.10.10: Offline-Vortest + schneller adaptiver Kombitest …")
    g=g.replace('text="SPEED + GELD TEST"','text="SPEED + GELD TEST (SCHNELL)"')

    old_speed = '''                    speed_result=core.compare_speed_1x_4x_6x(
                        self.hproc,self.hwnd,self.speed_info,
                        stop_event=self.speed_stop,expected_pid=self.pid,phase_duration=2.5
                    )
'''
    new_speed = '''                    speed_result=core.compare_speed_1x_4x_6x(
                        self.hproc,self.hwnd,self.speed_info,
                        stop_event=self.speed_stop,expected_pid=self.pid,phase_duration=1.20
                    )
                    empirical_speed=core.analyze_empirical_speed_response(speed_result)
                    print(
                        f"[KOMBITEST] Empirische Speed-Antwort: komplett={empirical_speed.get('complete_repeat_count')} | "
                        f"stabil={empirical_speed.get('stable_within_factor_count')} | "
                        f"stabil+monoton={empirical_speed.get('stable_monotonic_count')}"
                    )
'''
    if old_speed not in g:
        raise RuntimeError("Combined speed result anchor not found")
    g=g.replace(old_speed,new_speed,1)

    old_money='''                    self.money_addr=core.learn_money(self.hproc,self.hwnd)
'''
    new_money='''                    self.money_addr=core.learn_money_robust(self.hproc,self.hwnd)
'''
    if old_money not in g:
        raise RuntimeError("Combined money learner anchor not found")
    g=g.replace(old_money,new_money,1)

    g=g.replace('"version":"0.10.8",\n                        "method":"existing_learn_money_ctrl_m_3x_plus500",',
                '"version":"0.10.10",\n                        "method":"robust_ctrl_m_exact_first_then_polled_near500",',1)
    g=g.replace('"expected_test_side_effect_gold":1500,\n                        "direct_memory_write_used":False,\n                        "note":"Bestehende STRG+M-Routine: drei +500-Schritte; kein Kandidat wird blind beschrieben.",',
                '"nominal_max_added_gold":3000,\n                        "maximum_ctrl_m_pulses":6,\n                        "actual_effect_can_be_lower_on_missed_pulse":True,\n                        "direct_memory_write_used":False,\n                        "note":"Robuste Ctrl+M-Suche: erster Scan exakt +500, danach gepollte Wiederholungsbestaetigung; kein Kandidat wird blind beschrieben.",',1)
    g=g.replace('"Hinweis: Der Geldtest benutzt 3x STRG+M und fügt dadurch insgesamt 1500 Gold hinzu."',
                '"Hinweis: Der schnelle Geldtest nutzt bis zu 4 STRG+M-Pulse; nominal maximal +2000 Gold, bei verpassten Pulsen weniger."',1)
    g=g.replace('"version":"0.10.8","found":False,"error":str(exc)',
                '"version":"0.10.10","found":False,"error":str(exc)',1)
    g=g.replace('"version":"0.10.8",\n                    "kind":"combined_speed_money_test",',
                '"version":"0.10.10",\n                    "kind":"combined_speed_money_test",',1)
    # Add empirical counts to combined result if the local variable exists.
    g=g.replace(
        '"restore_to_1x":restore_diag,\n                    },\n                    "money":money_diag,',
        '"restore_to_1x":restore_diag,\n                        "empirical":empirical_speed if speed_result else None,\n                    },\n                    "money":money_diag,',1
    )
    gui.write_text(g,encoding="utf-8")

    _replace_exact(updater,'CURRENT_VERSION = "0.10.9"','CURRENT_VERSION = "0.10.10"',1)

    (root/"CHANGELOG_V0_10_10.md").write_text(
        "# V0.10.10\n\n"
        "- Bestehende Speed-Pass-Grenzen NICHT gelockert.\n"
        "- Offline/no-graphics Vortest liest den letzten Messlauf und waehlt nur die kuerzeren Zeitfenster; keine alten Adressen werden uebernommen.\n"
        "- Live-Speedtest deutlich kuerzer; nur bei zu duennen Rate-Daten ein automatischer 3s-Retry.\n"
        "- Neue empirische 1x/2x/4x-Auswertung fuer wiederholbare reale Standard-Speed-Kurven.\n"
        "- Robuste Geldsuche: erster Treffer exakt +500; Folgepulse kurz gepollt; maximal 4 Pulse.\n"
        "- Fehlender/verzoegerter Ctrl+M-Puls verwirft Kandidaten nicht mehr sofort.\n"
        "- Keine direkten Geld-Writes.\n"
        "- Dient zugleich als erster realer Smoke-Test fuer den V0.10.9 Safe-Staging-Updater.\n",
        encoding="utf-8",
    )
