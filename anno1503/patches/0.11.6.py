"""Anno 1503 Auto Trainer V0.11.6 - effective simulation speed curve.

Measures real in-game counter rates for requested speed factors instead of merely
confirming the writable multiplier value. Uses already calibrated same-session
counters; no full memory scan and no money test.
"""
from pathlib import Path

VERSION = "0.11.6"


def _replace_exact(path: Path, old: str, new: str, count: int | None = None):
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual == 0:
        raise RuntimeError(f"Expected text not found in {path.name}: {old!r}")
    if count is not None and actual != count:
        raise RuntimeError(f"Unexpected occurrence count in {path.name}: {actual} != {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root):
    root=Path(root)
    core=root/'Anno1503_AutoTrainer.py'
    gui=root/'Anno1503_AutoTrainer_GUI.py'
    updater=root/'updater.py'
    for p in (core,gui,updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    _replace_exact(core,'TRAINER_VERSION = "0.11.5"','TRAINER_VERSION = "0.11.6"',1)

    anchor='''def learn_money_robust(hproc, hwnd, required_hits=3, max_pulses=4, poll_timeout=0.45,\n'''
    helper=r'''def load_same_session_effective_speed_counters(hproc, expected_pid, speed_info, max_count=2):
    """Return previously calibrated game counters for the same live Anno process."""
    try:
        pid=int(expected_pid)
        speed_addr=int(speed_info["addr"])
    except Exception:
        return {"source_run":None,"addresses":[],"candidates":[]}
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
            if int(str(binding.get("address")),16) != speed_addr:
                continue
            rows=[]
            for row in data.get("calibrated_candidates") or []:
                if row.get("calibration_fail_reasons"):
                    continue
                try:
                    addr=int(str(row.get("address")),16)
                except Exception:
                    continue
                if read_u32(hproc,addr) is None:
                    continue
                stable6=(row.get("spread_6x_ratio") is not None)
                rows.append((not stable6,float(row.get("calibration_score") or 999),addr,row))
            rows.sort(key=lambda x:(x[0],x[1],x[2]))
            picked=rows[:max(1,int(max_count))]
            if picked:
                return {
                    "source_run":run.name,
                    "addresses":[x[2] for x in picked],
                    "candidates":[x[3] for x in picked],
                }
        except Exception:
            continue
    return {"source_run":None,"addresses":[],"candidates":[]}


'''
    if 'def load_same_session_effective_speed_counters(' not in core.read_text(encoding='utf-8'):
        _replace_exact(core,anchor,helper+anchor,1)

    g=gui.read_text(encoding='utf-8')
    button_anchor='''        self.speedstress_btn.pack(side="left")\n'''
    button_new=button_anchor+'''        self.effectivespeed_btn = ttk.Button(\n            stress_actions, text="ECHTE SPEED MESSEN", command=self.start_effective_speed_test\n        )\n        self.effectivespeed_btn.pack(side="left", padx=8)\n'''
    if 'text="ECHTE SPEED MESSEN"' not in g:
        if button_anchor not in g: raise RuntimeError('Stress button anchor missing')
        g=g.replace(button_anchor,button_new,1)

    state_anchor='''            self.speedstress_btn.configure(state=state)\n'''
    if 'self.effectivespeed_btn.configure(state=state)' not in g:
        if state_anchor not in g: raise RuntimeError('Stress state anchor missing')
        g=g.replace(state_anchor,state_anchor+'''            self.effectivespeed_btn.configure(state=state)\n''',1)

    method_anchor='''    # V0115_ESCALATING_SPEED_STRESS_TEST\n'''
    methods=r'''    # V0116_EFFECTIVE_SPEED_CURVE
    def start_effective_speed_test(self):
        if self.busy or self._speed_action_active():
            messagebox.showinfo("Anno 1503", "Es laeuft gerade bereits eine andere Trainer-/Speed-Aktion.")
            return
        if self.freeze_thread and self.freeze_thread.is_alive():
            messagebox.showinfo("Anno 1503", "Freeze zuerst stoppen.")
            return
        if not self._ensure_game_for_speed():
            messagebox.showinfo("Anno 1503", "Anno starten und denselben Spielstand laden.")
            return
        self.busy=True
        self.speed_stop.clear()
        self._set_speed_buttons(False)
        self.speed_thread=threading.Thread(target=self._effective_speed_worker,daemon=True)
        self.speed_thread.start()

    def _effective_speed_worker(self):
        factors=(1.0,2.0,4.0,6.0,8.0,10.0,12.0,16.0,24.0,32.0,48.0,64.0,96.0,128.0,1.0)
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        phases=[]
        result=None
        error=None
        final_restore=None
        started=time.monotonic()
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[ECHTE-SPEED] Messe reale Spielzaehler-Rate 1x bis 128x. Kein Vollscan, kein Geldtest.")
                self._set_status("Echte Speed: Speed-Adresse und Spielzaehler bestaetigen ...")

                if self.speed_info:
                    ok,_,reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok:
                        print(f"[ECHTE-SPEED] alter Speed-Kandidat verworfen: {reason}")
                        self.speed_info=None
                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info:
                    raise RuntimeError("Kein gueltiger Same-Session-Speed-Cache; kein Vollscan als Fallback.")

                binding=core.verify_speed_binding_with_f5(
                    self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid
                )
                counters=core.load_same_session_effective_speed_counters(
                    self.hproc,self.pid,self.speed_info,max_count=2
                )
                addresses=list(counters.get("addresses") or [])
                if not addresses:
                    raise RuntimeError("Kein bereits kalibrierter Spielzaehler derselben Anno-Sitzung gefunden.")
                print(f"[ECHTE-SPEED] Zaehler aus {counters.get('source_run')}: {[hex(a) for a in addresses]}")

                for idx,factor in enumerate(factors,1):
                    core._raise_if_stopped(self.speed_stop,"Echte-Speed-Messung")
                    duration=0.65 if factor <= 16 else 0.50
                    self._set_status(f"Echte Speed messen: {factor:g}x ({idx}/{len(factors)}) ...")
                    reset,phase=core._run_calibration_phase(
                        self.hproc,self.hwnd,self.speed_info,addresses,factor,duration,
                        stop_event=self.speed_stop,expected_pid=self.pid
                    )
                    phases.append({"reset":reset,"phase":phase})
                    print(f"[ECHTE-SPEED] {factor:g}x rates={phase.get('rates')}")

                # Baseline uses both 1x measurements (start/end) to reduce drift.
                baseline_by_addr={}
                for addr in addresses:
                    vals=[]
                    for row in phases:
                        ph=row["phase"]
                        if abs(float(ph.get("factor") or 0)-1.0) <= 1e-6:
                            rv=(ph.get("rates") or {}).get(addr)
                            if rv is not None and float(rv)>0:
                                vals.append(float(rv))
                    if vals:
                        baseline_by_addr[addr]=statistics.median(vals)
                if not baseline_by_addr:
                    raise RuntimeError("Keine gueltige 1x-Basisrate gemessen.")

                curve=[]
                for row in phases[:-1]:
                    ph=row["phase"]
                    factor=float(ph.get("factor") or 0)
                    ratios=[]
                    rates_out={}
                    for addr in addresses:
                        rv=(ph.get("rates") or {}).get(addr)
                        base=baseline_by_addr.get(addr)
                        if rv is not None and base and float(rv)>0:
                            rates_out[hex(addr)]=float(rv)
                            ratios.append(float(rv)/float(base))
                    eff=statistics.median(ratios) if ratios else None
                    curve.append({
                        "requested_factor":factor,
                        "effective_ratio_vs_1x":eff,
                        "counter_rates":rates_out,
                        "counter_ratios":ratios,
                    })

                valid=[x for x in curve if x.get("effective_ratio_vs_1x") is not None]
                max_eff=max((float(x["effective_ratio_vs_1x"]) for x in valid),default=None)
                plateau=None
                if max_eff is not None and max_eff>0:
                    threshold=max_eff*0.95
                    for x in valid:
                        if float(x["effective_ratio_vs_1x"]) >= threshold:
                            plateau=float(x["requested_factor"])
                            break
                result={
                    "version":"0.11.6",
                    "kind":"effective_simulation_speed_curve",
                    "binding":binding,
                    "counter_source_run":counters.get("source_run"),
                    "counter_addresses":[hex(a) for a in addresses],
                    "baseline_rates":{hex(a):v for a,v in baseline_by_addr.items()},
                    "curve":curve,
                    "max_effective_ratio_vs_1x":max_eff,
                    "plateau_start_requested_factor_95pct":plateau,
                    "full_memory_scan_used":False,
                    "money_test_used":False,
                    "elapsed_total_sec":round(time.monotonic()-started,4),
                }
                print(f"[ECHTE-SPEED] Max effektiv ~{max_eff:.2f}x; 95%-Plateau ab angefordert ~{plateau:g}x" if max_eff and plateau else "[ECHTE-SPEED] Plateau nicht bestimmbar")
        except InterruptedError as exc:
            error=f"abgebrochen: {exc}"
            print(f"[ECHTE-SPEED] {error}")
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
            print(f"[ECHTE-SPEED FEHLER] {error}")
            traceback.print_exc()
        finally:
            try:
                if self.hproc and self.speed_info:
                    final_restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25
                    )
            except Exception as exc:
                final_restore={"verified":False,"error":str(exc)}
            payload=result or {
                "version":"0.11.6","kind":"effective_simulation_speed_curve",
                "full_memory_scan_used":False,"money_test_used":False,"error":error,
                "elapsed_total_sec":round(time.monotonic()-started,4),
            }
            payload["final_restore_to_1x"]=final_restore
            if error: payload["error"]=error
            try:
                if core.RUN_DIR:
                    (core.RUN_DIR/"effective_speed_curve.json").write_text(
                        json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()

            if not self.closing:
                if result and result.get("curve"):
                    lines=[]
                    for x in result["curve"]:
                        eff=x.get("effective_ratio_vs_1x")
                        lines.append(f"{x['requested_factor']:g}x -> effektiv ~{eff:.2f}x" if eff is not None else f"{x['requested_factor']:g}x -> keine Rate")
                    msg=(
                        "Echte Simulationsgeschwindigkeit gemessen.\n\n"+
                        "\n".join(lines)+"\n\n"+
                        f"Maximum effektiv: ~{result.get('max_effective_ratio_vs_1x'):.2f}x\n"+
                        f"Plateau (95% vom Maximum) ab angefordert: ~{result.get('plateau_start_requested_factor_95pct'):g}x\n"+
                        f"1x-Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                    )
                else:
                    msg=f"Echte-Speed-Messung fehlgeschlagen.\n\n{error or 'unbekannter Fehler'}"
                self.q.put(("effectivespeed_result",msg))
            self._set_status("Echte-Speed-Messung fertig; Ergebnis fuer ChatGPT bereit.")
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

'''
    if 'def start_effective_speed_test(' not in g:
        if method_anchor not in g: raise RuntimeError('Stress method anchor missing')
        g=g.replace(method_anchor,methods+method_anchor,1)

    poll_anchor='''                elif kind == "speedstress_result":\n                    messagebox.showinfo("Speed-Stresstest", val)\n'''
    if 'elif kind == "effectivespeed_result":' not in g:
        if poll_anchor not in g: raise RuntimeError('Stress poll anchor missing')
        g=g.replace(poll_anchor,poll_anchor+'''                elif kind == "effectivespeed_result":\n                    messagebox.showinfo("Echte Simulationsgeschwindigkeit", val)\n''',1)

    gui.write_text(g,encoding='utf-8')
    _replace_exact(updater,'CURRENT_VERSION = "0.11.5"','CURRENT_VERSION = "0.11.6"',1)
    (root/'CHANGELOG_V0_11_6.md').write_text(
        '# V0.11.6 - Echte Simulationsgeschwindigkeit\n\n'
        '- Neuer Kurztest misst reale Spielzaehler-Raten statt nur den geschriebenen Speed-Faktor.\n'
        '- Faktoren: 1/2/4/6/8/10/12/16/24/32/48/64/96/128x.\n'
        '- Verwendet bis zu zwei bereits kalibrierte Zaehler derselben Anno-Sitzung.\n'
        '- Kein Vollscan, kein Geldtest.\n'
        '- Bestimmt Maximum effektiv und 95%-Plateau.\n'
        '- Finale Rueckstellung auf 1x bleibt Pflicht.\n',encoding='utf-8'
    )
