"""Anno 1503 Auto Trainer V0.11.9 - minimized turbo curve.

Measures the real simulation-rate ceiling while Anno is minimized, where V0.11.8
showed a large rendering bottleneck. No full scan, no money test, no game-file
changes. Restores the window and verified 1x in finally.
"""
from pathlib import Path

VERSION = "0.11.9"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.11.8"', 'TRAINER_VERSION = "0.11.9"', 1)

    g = gui.read_text(encoding="utf-8")

    button_anchor = '''        self.cpurender_btn = ttk.Button(\n            stress_actions, text="CPU/GRAFIK A/B", command=self.start_cpu_render_test\n        )\n        self.cpurender_btn.pack(side="left", padx=8)\n'''
    if button_anchor not in g:
        raise RuntimeError("CPU/Grafik button anchor not found")
    button_new = button_anchor + '''        self.miniturbo_btn = ttk.Button(\n            stress_actions, text="MINI-TURBO KURVE", command=self.start_minimized_turbo_test\n        )\n        self.miniturbo_btn.pack(side="left", padx=8)\n'''
    g = g.replace(button_anchor, button_new, 1)

    state_anchor = '''            self.cpurender_btn.configure(state=state)\n'''
    if state_anchor not in g:
        raise RuntimeError("CPU/Grafik state anchor not found")
    g = g.replace(state_anchor, state_anchor + '            self.miniturbo_btn.configure(state=state)\n', 1)

    method_anchor = '''    # V0118_CPU_RENDER_AB\n    def start_cpu_render_test(self):\n'''
    if method_anchor not in g:
        raise RuntimeError("CPU/Grafik method anchor not found")

    methods = r'''    # V0119_MINIMIZED_TURBO_CURVE
    def start_minimized_turbo_test(self):
        if self.busy or self._speed_action_active():
            messagebox.showinfo("Anno 1503", "Es laeuft gerade bereits eine andere Trainer-/Speed-Aktion.")
            return
        if self.freeze_thread and self.freeze_thread.is_alive():
            messagebox.showinfo("Anno 1503", "Freeze zuerst stoppen.")
            return
        if not self._ensure_game_for_speed():
            messagebox.showinfo("Anno 1503", "Anno starten und denselben Test-Spielstand laden.")
            return
        self.busy=True
        self.speed_stop.clear()
        self._set_speed_buttons(False)
        self.speed_thread=threading.Thread(target=self._minimized_turbo_worker,daemon=True)
        self.speed_thread.start()

    def _minimized_turbo_worker(self):
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        rows=[]; error=None; final_restore=None; result=None
        started=time.monotonic()
        factors=[32.0,48.0,64.0,96.0,128.0,192.0,256.0,384.0,512.0,768.0,1024.0]
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[MINI-TURBO] Reale Speed-Kurve minimiert: 32x bis 1024x.")

                if self.speed_info:
                    ok,_,reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok:
                        print(f"[MINI-TURBO] alter Speed-Kandidat verworfen: {reason}")
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
                    raise RuntimeError("Kein kalibrierter Spielzaehler derselben Anno-Sitzung gefunden.")
                print(f"[MINI-TURBO] Zaehler: {[hex(a) for a in addresses]} aus {counters.get('source_run')}")

                self._set_status("Mini-Turbo: 1x-Basis sichtbar messen ...")
                core.set_game_window_minimized(self.hwnd,minimized=False,settle=0.20)
                core.focus_game(self.hwnd,verify=False)
                base=core.measure_effective_counter_cpu_window(
                    self.hproc,self.speed_info,addresses,1.0,duration=0.80,
                    expected_pid=self.pid,stop_event=self.speed_stop
                )
                base["label"]="1X_VISIBLE_BASE"
                base["actual_minimized"]=False
                rows.append(base)
                base_rate=float(base.get("median_rate") or 0)
                if base_rate <= 0:
                    raise RuntimeError("1x-Basisrate konnte nicht gemessen werden.")
                print(f"[MINI-TURBO] Basis 1x: rate={base_rate:.3f} | CPU={base.get('cpu_core_equivalents'):.3f} core")

                self._set_status("Mini-Turbo: Anno minimieren ...")
                core.set_game_window_minimized(self.hwnd,minimized=True,settle=0.25)
                if not core.is_window_minimized(self.hwnd):
                    raise RuntimeError("Anno-Fenster konnte nicht minimiert werden.")

                best=None
                for factor in factors:
                    self._set_status(f"Mini-Turbo: {factor:g}x minimiert messen ...")
                    row=core.measure_effective_counter_cpu_window(
                        self.hproc,self.speed_info,addresses,factor,duration=0.72,
                        expected_pid=self.pid,stop_event=self.speed_stop
                    )
                    rate=float(row.get("median_rate") or 0)
                    eff=(rate/base_rate) if rate>0 else None
                    row["label"]=f"{factor:g}X_MINIMIZED"
                    row["actual_minimized"]=bool(core.is_window_minimized(self.hwnd))
                    row["effective_vs_1x"]=eff
                    rows.append(row)
                    if eff is not None and (best is None or eff>best["effective_vs_1x"]):
                        best={"factor":factor,"effective_vs_1x":eff,"rate":rate,
                              "cpu_core_equivalents":float(row.get("cpu_core_equivalents") or 0)}
                    print(
                        f"[MINI-TURBO] {factor:g}x: real={eff:.2f}x | rate={rate:.2f} | "
                        f"CPU={float(row.get('cpu_core_equivalents') or 0):.2f} core"
                        if eff is not None else
                        f"[MINI-TURBO] {factor:g}x: keine gueltige Rate"
                    )

                    # If three consecutive factors are clearly no better than the best,
                    # stop early instead of wasting time at ever higher written values.
                    valid=[r for r in rows[1:] if r.get("effective_vs_1x") is not None]
                    if len(valid)>=4 and best is not None:
                        tail=valid[-3:]
                        if all(float(r["effective_vs_1x"]) <= float(best["effective_vs_1x"])*0.93 for r in tail):
                            print("[MINI-TURBO] Plateau/Abfall ueber drei Stufen erkannt; Test endet frueh.")
                            break

                result={
                    "version":"0.11.9",
                    "kind":"minimized_turbo_curve",
                    "binding":binding,
                    "counter_source_run":counters.get("source_run"),
                    "counter_addresses":[hex(a) for a in addresses],
                    "factors_requested":factors,
                    "rows":rows,
                    "best":best,
                    "full_memory_scan_used":False,
                    "money_test_used":False,
                    "game_files_modified":False,
                    "window_minimized_during_turbo":True,
                    "elapsed_total_sec":round(time.monotonic()-started,4),
                }
        except InterruptedError as exc:
            error=f"abgebrochen: {exc}"
            print(f"[MINI-TURBO] {error}")
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
            print(f"[MINI-TURBO FEHLER] {error}")
            traceback.print_exc()
        finally:
            # First force 1x directly even while minimized, then restore window and
            # perform the existing focus/F5/readback safety restore.
            try:
                if self.hproc and self.speed_info:
                    core.set_custom_speed(self.hproc,self.speed_info,1.0)
                    time.sleep(0.10)
            except Exception:
                pass
            try:
                core.set_game_window_minimized(self.hwnd,minimized=False,settle=0.22)
            except Exception as exc:
                print(f"[MINI-TURBO] Fenster-Restore Warnung: {exc}")
            try:
                if self.hproc and self.speed_info:
                    final_restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25
                    )
            except Exception as exc:
                final_restore={"verified":False,"error":str(exc)}

            payload=result or {
                "version":"0.11.9","kind":"minimized_turbo_curve","rows":rows,
                "error":error,"full_memory_scan_used":False,"money_test_used":False,
                "game_files_modified":False,"elapsed_total_sec":round(time.monotonic()-started,4),
            }
            payload["final_restore_to_1x"]=final_restore
            if error:
                payload["error"]=error
            try:
                if core.RUN_DIR:
                    (core.RUN_DIR/"minimized_turbo_curve.json").write_text(
                        json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()

            if not self.closing:
                if result and result.get("best"):
                    best=result["best"]
                    msg=(
                        "Mini-Turbo-Kurve beendet.\n\n"
                        f"Beste Einstellung: {best.get('factor'):g}x\n"
                        f"Reale Geschwindigkeit: {best.get('effective_vs_1x'):.2f}x\n"
                        f"CPU dabei: {best.get('cpu_core_equivalents'):.2f} Kerne\n"
                        f"Gemessene Turbo-Stufen: {len(rows)-1}\n\n"
                        f"1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                    )
                else:
                    msg=(
                        "Mini-Turbo-Kurve nicht abgeschlossen.\n\n"
                        f"Grund: {error or 'unbekannt'}\n"
                        f"1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                    )
                self.q.put(("minimized_turbo_result",msg))
            self._set_status(
                "Mini-Turbo fertig; 1x wiederhergestellt."
                if final_restore and final_restore.get("verified")
                else "Mini-Turbo fertig; Rueckstellung pruefen."
            )
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

'''
    g = g.replace(method_anchor, methods + method_anchor, 1)

    poll_anchor = '''                elif kind == "cpu_render_result":\n                    messagebox.showinfo("CPU/Grafik A/B", val)\n'''
    if poll_anchor not in g:
        raise RuntimeError("CPU/Grafik poll anchor not found")
    g = g.replace(
        poll_anchor,
        poll_anchor + '                elif kind == "minimized_turbo_result":\n                    messagebox.showinfo("Mini-Turbo-Kurve", val)\n',
        1,
    )

    gui.write_text(g,encoding="utf-8")
    _replace_exact(updater,'CURRENT_VERSION = "0.11.8"','CURRENT_VERSION = "0.11.9"',1)

    (root/"CHANGELOG_V0_11_9.md").write_text(
        "# V0.11.9 - Mini-Turbo-Kurve\n\n"
        "- Misst reale Simulationsgeschwindigkeit bei minimiertem Anno-Fenster.\n"
        "- Faktoren: 32/48/64/96/128/192/256/384/512/768/1024x.\n"
        "- Kurze 0.72s-Fenster; echter Spielzaehler + Prozess-CPU.\n"
        "- Automatischer Fruehabbruch bei klarem Plateau/Abfall.\n"
        "- Kein Vollscan, kein Geldtest, keine Spieldatei-Aenderung.\n"
        "- Finale Fenster-Wiederherstellung und 1x-Readback-Pflicht.\n",
        encoding="utf-8",
    )
