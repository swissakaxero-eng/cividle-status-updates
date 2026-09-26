"""Anno 1503 Auto Trainer V0.10.11 - same-session cache fast path.

Repeated tests in the SAME Anno1503.exe process avoid repeated ~1.17 GB
memory scans. Previous result files are only hints for the same PID; the cached
speed address is re-validated live with F5 -> 1.0 before reuse.
"""
from pathlib import Path

VERSION = "0.10.11"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.10.10"', 'TRAINER_VERSION = "0.10.11"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.10',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.11',
        1,
    )

    money_anchor = 'def learn_money_robust(hproc, hwnd, required_hits=3, max_pulses=4, poll_timeout=0.45,\n'
    helper = r'''def load_same_session_history(expected_pid):
    """Read previous result JSON only for the same Anno PID."""
    try:
        pid=int(expected_pid)
    except Exception:
        return None
    runs=sorted(
        [p for p in get_results_dir().glob("RUN_*") if p.is_dir()],
        key=lambda p:p.stat().st_mtime, reverse=True
    )
    for run in runs:
        fp=run/"speed_compare_1x_2x_4x_calibrated_6x.json"
        if not fp.is_file():
            continue
        try:
            data=json.loads(fp.read_text(encoding="utf-8"))
            binding=data.get("binding") or {}
            if int(binding.get("pid") or -1) != pid:
                continue
            addr=int(str(binding.get("address")),16)
            width_bits=int(binding.get("width_bits") or 0)
            if width_bits not in (32,64):
                continue

            counters=[]
            for row in data.get("targeted_candidate_activity") or []:
                try:
                    counters.append(int(str(row.get("address")),16))
                except Exception:
                    pass
            if not counters:
                for phase in data.get("targeted_confirmation_phases") or []:
                    for key in (phase.get("rates") or {}):
                        try:
                            counters.append(int(str(key),16))
                        except Exception:
                            pass
            seen=set()
            counters=[a for a in counters if not (a in seen or seen.add(a))]

            money=[]
            mf=run/"money_learning_robust.json"
            if mf.is_file():
                try:
                    md=json.loads(mf.read_text(encoding="utf-8"))
                    for key in md.get("initial_candidates") or md.get("remaining_candidates") or []:
                        try:
                            money.append(int(str(key),16))
                        except Exception:
                            pass
                except Exception:
                    pass
            seen=set()
            money=[a for a in money if not (a in seen or seen.add(a))]

            return {
                "source_run":run.name,
                "pid":pid,
                "speed_info":{"addr":addr,"width":width_bits//8},
                "counter_addresses":counters[:64],
                "money_candidates":money[:64],
            }
        except Exception:
            continue
    return None


def load_same_session_speed_info(hproc, hwnd, expected_pid):
    hist=load_same_session_history(expected_pid)
    if not hist:
        return None
    info=hist.get("speed_info")
    try:
        ok, _, reason=validate_speed_info(hproc,info,expected_pid)
        if not ok:
            print(f"[SESSION-CACHE] Speed-Hinweis verworfen: {reason}")
            return None
        proof=verify_speed_binding_with_f5(hproc,hwnd,info,expected_pid=expected_pid)
        print(
            f"[SESSION-CACHE] Speed aus {hist.get('source_run')} wiederverwendet und live bestaetigt: "
            f"{proof.get('address')} -> {proof.get('f5_readback')}"
        )
        return info
    except Exception as exc:
        print(f"[SESSION-CACHE] Speed-Hinweis nicht verwendbar: {exc}")
        return None


def load_same_session_counter_addresses(hproc, expected_pid, speed_info):
    hist=load_same_session_history(expected_pid)
    if not hist or not speed_info:
        return {"source_run":None,"addresses":[]}
    try:
        if int(hist["speed_info"]["addr"]) != int(speed_info["addr"]):
            return {"source_run":hist.get("source_run"),"addresses":[]}
    except Exception:
        return {"source_run":hist.get("source_run"),"addresses":[]}
    out=[]
    for addr in hist.get("counter_addresses") or []:
        try:
            if int(addr) == int(speed_info["addr"]):
                continue
            if read_u32(hproc,int(addr)) is not None:
                out.append(int(addr))
        except Exception:
            pass
    out=list(dict.fromkeys(out))[:32]
    return {"source_run":hist.get("source_run"),"addresses":out}


'''
    _replace_exact(core, money_anchor, helper + money_anchor, 1)

    _replace_exact(
        core,
        'def learn_money_robust(hproc, hwnd, required_hits=3, max_pulses=4, poll_timeout=0.45,\n'
        '                       tolerance=20):',
        'def learn_money_robust(hproc, hwnd, required_hits=3, max_pulses=4, poll_timeout=0.45,\n'
        '                       tolerance=20, expected_pid=None, speed_info=None):',
        1,
    )

    old_money_start = r'''    print("\n[GELD V0.10.10] robuste Geldsuche startet.")
    focus_game(hwnd)
    before,total=snapshot_regions(hproc)
    chord(VK_CONTROL,VK_M)
    time.sleep(0.20)
    cand=set(diff_plus_32(before,hproc,500))
    print(f"  Kandidaten nach erstem exakten +500: {len(cand)}")
    diag={
'''
    new_money_start = r'''    print("\n[GELD V0.10.11] schnelle Geldsuche startet.")
    hist=load_same_session_history(expected_pid) if expected_pid is not None else None
    cached=[]
    if hist and speed_info:
        try:
            if int(hist["speed_info"]["addr"]) == int(speed_info["addr"]):
                for a in hist.get("money_candidates") or []:
                    if read_i32(hproc,int(a)) is not None:
                        cached.append(int(a))
        except Exception:
            cached=[]
    cached=list(dict.fromkeys(cached))[:64]

    if cached:
        cand=set(cached)
        total=0
        pulse=0
        hits={a:0 for a in cand}
        discovery_mode="same_session_cached_money_candidates"
        print(
            f"  [SESSION-CACHE] {len(cand)} Geldkandidat(en) aus {hist.get('source_run')} "
            "ohne Vollscan erneut pruefen."
        )
    else:
        focus_game(hwnd)
        before,total=snapshot_regions(hproc)
        chord(VK_CONTROL,VK_M)
        time.sleep(0.20)
        cand=set(diff_plus_32(before,hproc,500))
        pulse=1
        hits={a:1 for a in cand}
        discovery_mode="full_scan_first_exact_plus500"
        print(f"  Kandidaten nach erstem exakten +500: {len(cand)}")

    diag={
'''
    _replace_exact(core, old_money_start, new_money_start, 1)

    _replace_exact(
        core,
        '''        "memory_bytes_scanned":total,
        "required_hits":int(required_hits),
''',
        '''        "memory_bytes_scanned":total,
        "discovery_mode":discovery_mode,
        "history_source_run":hist.get("source_run") if hist else None,
        "required_hits":int(required_hits),
''',
        1,
    )

    _replace_exact(
        core,
        '''    hits={a:1 for a in cand}
    pulse=1

    while cand and pulse < int(max_pulses):
''',
        '''    while cand and pulse < int(max_pulses):
''',
        1,
    )

    old_discovery = '''        print("[SPEED-KALIBRIERUNG] Suche bei 1x unabhängige steigende 32-Bit-Zähler …")
        candidates,total,discover_elapsed=_discover_changing_u32_candidates(
            hproc, duration=1.20, stop_event=stop_event, max_candidates=8000
        )
        addresses=[a for a,_,_ in candidates if a != int(speed_info['addr'])]
        print(f"[SPEED-KALIBRIERUNG] {len(addresses)} Kandidaten aus {total/1024/1024:.1f} MiB Snapshot.")
        if len(addresses) < 10:
            raise RuntimeError("Zu wenige unabhängige Zählerkandidaten.")

        # 6x darf die Auswahl NICHT beeinflussen.
'''
    new_discovery = '''        cache_hint=load_same_session_counter_addresses(hproc,expected_pid,speed_info)
        cached_addresses=list(cache_hint.get("addresses") or [])
        cache_mode=len(cached_addresses) >= 8
        if cache_mode:
            addresses=cached_addresses
            total=0
            discover_elapsed=0.0
            candidate_source="same_session_result_cache"
            phase_duration=max(
                float(phase_duration),
                float(offline_hint.get("targeted_duration_sec",1.25))
            )
            print(
                f"[SPEED-SESSION-CACHE] {len(addresses)} bereits gemessene Kandidaten aus "
                f"{cache_hint.get('source_run')} wiederverwendet; 1.17-GB-Vollscan entfaellt."
            )
        else:
            candidate_source="full_memory_discovery"
            print("[SPEED-KALIBRIERUNG] Suche bei 1x unabhängige steigende 32-Bit-Zähler …")
            candidates,total,discover_elapsed=_discover_changing_u32_candidates(
                hproc, duration=1.20, stop_event=stop_event, max_candidates=8000
            )
            addresses=[a for a,_,_ in candidates if a != int(speed_info['addr'])]
            print(f"[SPEED-KALIBRIERUNG] {len(addresses)} Kandidaten aus {total/1024/1024:.1f} MiB Snapshot.")
            if len(addresses) < 10:
                raise RuntimeError("Zu wenige unabhängige Zählerkandidaten.")

        # 6x darf die Auswahl NICHT beeinflussen.
'''
    _replace_exact(core, old_discovery, new_discovery, 1)

    _replace_exact(
        core,
        '''        confirmation_used=False
        targeted_retry_used=False
        calibration_for_final=calibration_runs
        pre_for_final=pre

        if pre.get("calibrated_count",0) == 0:
''',
        '''        confirmation_used=False
        targeted_retry_used=False
        calibration_for_final=calibration_runs
        pre_for_final=pre

        if cache_mode:
            confirmation_used=True
            confirmation_addresses=list(addresses)
            confirmation_runs=list(calibration_runs)
            confirmation_duration=float(phase_duration)
            print("[SPEED-SESSION-CACHE] Standardlauf dient zugleich als gezielte Bestaetigung; keine zweite 9-Phasen-Runde.")
        elif pre.get("calibrated_count",0) == 0:
''',
        1,
    )

    _replace_exact(
        core,
        '''            "discovery":{
                "snapshot_bytes":total,
                "elapsed_sec":discover_elapsed,
                "candidate_count":len(addresses),
            },
''',
        '''            "discovery":{
                "source":candidate_source,
                "snapshot_bytes":total,
                "elapsed_sec":discover_elapsed,
                "candidate_count":len(addresses),
            },
''',
        1,
    )

    g=gui.read_text(encoding="utf-8")
    g=g.replace("Anno 1503 Auto Trainer V0.10.10 PERMANENT BOOTSTRAP",
                "Anno 1503 Auto Trainer V0.10.11 PERMANENT BOOTSTRAP")
    g=g.replace('"version":"0.10.10"','"version":"0.10.11"')
    g=g.replace("V0.10.10: Offline-Vortest + schneller adaptiver Kombitest …",
                "V0.10.11: Session-Cache; Vollscans bei gleicher Anno-Sitzung vermeiden …")
    g=g.replace('text="SPEED + GELD TEST (SCHNELL)"',
                'text="SPEED + GELD TEST (CACHE)"')

    old_speed_learn = '''                    if not self.speed_info:
                        self.speed_info=core.learn_speed_factor(
                            self.hproc,self.hwnd,stop_event=self.speed_stop,expected_pid=self.pid
                        )
'''
    new_speed_learn = '''                    if not self.speed_info:
                        self.speed_info=core.load_same_session_speed_info(
                            self.hproc,self.hwnd,self.pid
                        )
                    if not self.speed_info:
                        print("[KOMBITEST] Kein gueltiger Session-Cache; einmalige volle Speed-Suche noetig.")
                        self.speed_info=core.learn_speed_factor(
                            self.hproc,self.hwnd,stop_event=self.speed_stop,expected_pid=self.pid
                        )
'''
    if old_speed_learn not in g:
        raise RuntimeError("GUI speed learn anchor not found")
    g=g.replace(old_speed_learn,new_speed_learn,1)

    old_money_call='''                    self.money_addr=core.learn_money_robust(self.hproc,self.hwnd)
'''
    new_money_call='''                    self.money_addr=core.learn_money_robust(
                        self.hproc,self.hwnd,expected_pid=self.pid,speed_info=self.speed_info
                    )
'''
    if old_money_call not in g:
        raise RuntimeError("GUI money call anchor not found")
    g=g.replace(old_money_call,new_money_call,1)

    g=g.replace('"version":"0.10.10",\n                        "method":"existing_learn_money_ctrl_m_3x_plus500",',
                '"version":"0.10.11",\n                        "method":"same_session_cache_then_robust_ctrl_m",',1)
    g=g.replace('"version":"0.10.10","found":False,"error":str(exc)',
                '"version":"0.10.11","found":False,"error":str(exc)',1)
    g=g.replace('"version":"0.10.10",\n                    "kind":"combined_speed_money_test",',
                '"version":"0.10.11",\n                    "kind":"combined_speed_money_test",',1)
    g=g.replace(
        '"Hinweis: Der schnelle Geldtest nutzt bis zu 4 STRG+M-Pulse; nominal maximal +2000 Gold, bei verpassten Pulsen weniger."',
        '"Hinweis: Bei gleicher Anno-Sitzung werden Speed-/Geldkandidaten aus dem letzten Run live neu geprueft; grosse Vollscans entfallen normalerweise."',1
    )
    gui.write_text(g,encoding="utf-8")

    _replace_exact(updater,'CURRENT_VERSION = "0.10.10"','CURRENT_VERSION = "0.10.11"',1)

    (root/"CHANGELOG_V0_10_11.md").write_text(
        "# V0.10.11\n\n"
        "- Same-session Cache: letzte Resultate nur bei identischer Anno-PID wiederverwenden.\n"
        "- Cached Speed-Adresse vor Nutzung live erneut mit F5 -> 1.0 beweisen.\n"
        "- Bei gueltigem Cache entfaellt die erneute ~1.17-GB-Speed-Faktorsuche.\n"
        "- Bis zu 32 bereits gemessene Zaehler ersetzen den 8000-Kandidaten-Vollscan.\n"
        "- Der 9-Phasen-Cachelauf dient direkt als Bestaetigung; keine doppelte 9-Phasen-Runde.\n"
        "- Geld: bei gleicher Sitzung zuerst den letzten kleinen Kandidatensatz pruefen; Vollscan nur bei Cache-Miss.\n"
        "- Keine Speed-Pass-Grenzen gelockert; keine direkten Geld-Writes.\n"
        "- Bei neuer Anno-PID automatischer Rueckfall auf die bestehenden Vollsuchen.\n",
        encoding="utf-8",
    )
