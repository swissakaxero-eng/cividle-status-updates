"""Anno 1503 Auto Trainer V0.11.10 - visible turbo optimizer + rendering comparison.

Uses the confirmed rendering bottleneck result to compare visible/minimized/hidden at 32x,
then fine-scan a practical VISIBLE turbo range so the game remains on screen and usable.
Persists the best visible profile for start/stop without a full scan.
"""
from pathlib import Path

VERSION = "0.11.10"


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
    core=root/"Anno1503_AutoTrainer.py"
    gui=root/"Anno1503_AutoTrainer_GUI.py"
    updater=root/"updater.py"
    for p in (core,gui,updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    _replace_exact(core,'TRAINER_VERSION = "0.11.9"','TRAINER_VERSION = "0.11.10"',1)

    profile_anchor='''def find_latest_result_zip():\n'''
    if 'def get_turbo_profile_path(' not in core.read_text(encoding='utf-8'):
        profile_helpers=r'''def get_turbo_profile_path():
    return get_profiles_dir() / "turbo_best_profile.json"


def save_turbo_profile(profile):
    p=get_turbo_profile_path()
    p.write_text(json.dumps(profile,indent=2,ensure_ascii=False),encoding="utf-8")
    return p


def load_turbo_profile():
    p=get_turbo_profile_path()
    if not p.is_file():
        return None
    try:
        obj=json.loads(p.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj,dict) else None
    except Exception:
        return None


'''
        _replace_exact(core,profile_anchor,profile_helpers+profile_anchor,1)

    hidden_anchor='''def measure_effective_counter_cpu_window(hproc, speed_info, addresses, factor, duration=0.9,\n'''
    if 'def set_game_window_hidden(' not in core.read_text(encoding='utf-8'):
        hidden_helpers=r'''def is_window_visible(hwnd):
    try:
        return bool(user32.IsWindowVisible(hwnd))
    except Exception:
        return False


def set_game_window_hidden(hwnd, hidden=True, settle=0.20):
    if not hwnd:
        raise RuntimeError("Anno-Fensterhandle fehlt")
    if hidden:
        user32.ShowWindow(hwnd,0)  # SW_HIDE
    else:
        user32.ShowWindow(hwnd,9)  # SW_RESTORE
        time.sleep(0.08)
        try:
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
    time.sleep(max(0.05,float(settle)))
    return not is_window_visible(hwnd)


def restore_game_window_visible(hwnd, settle=0.20):
    if not hwnd:
        return False
    user32.ShowWindow(hwnd,9)  # SW_RESTORE
    time.sleep(0.08)
    try:
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(max(0.05,float(settle)))
    return is_window_visible(hwnd)


'''
        _replace_exact(core,hidden_anchor,hidden_helpers+hidden_anchor,1)

    g=gui.read_text(encoding='utf-8')
    button_anchor='''        self.miniturbo_btn = ttk.Button(\n            stress_actions, text="MINI-TURBO KURVE", command=self.start_minimized_turbo_test\n        )\n        self.miniturbo_btn.pack(side="left", padx=8)\n'''
    if button_anchor not in g:
        raise RuntimeError('Mini-turbo button anchor not found')
    button_new=button_anchor+'''        self.turboopt_btn = ttk.Button(\n            stress_actions, text="TURBO OPTIMIEREN", command=self.start_turbo_optimizer\n        )\n        self.turboopt_btn.pack(side="left", padx=8)\n        self.turbobest_btn = ttk.Button(\n            stress_actions, text="TURBO SICHTBAR START", command=self.start_turbo_best\n        )\n        self.turbobest_btn.pack(side="left", padx=8)\n        self.turbostop_btn = ttk.Button(\n            stress_actions, text="TURBO STOP", command=self.stop_turbo_best, state="disabled"\n        )\n        self.turbostop_btn.pack(side="left", padx=8)\n'''
    g=g.replace(button_anchor,button_new,1)

    state_anchor='''            self.miniturbo_btn.configure(state=state)\n'''
    if state_anchor not in g:
        raise RuntimeError('Mini-turbo state anchor not found')
    g=g.replace(state_anchor,state_anchor+'''            self.turboopt_btn.configure(state=state)\n            self.turbobest_btn.configure(state=state)\n''',1)

    method_anchor='''    # V0119_MINIMIZED_TURBO_CURVE\n'''
    if method_anchor not in g:
        raise RuntimeError('Mini-turbo method anchor not found')
    methods=r'''    # V01110_TURBO_OPTIMIZER_AND_BEST_MODE
    def start_turbo_optimizer(self):
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
        try:
            self.turbostop_btn.configure(state="disabled")
        except Exception:
            pass
        self.speed_thread=threading.Thread(target=self._turbo_optimizer_worker,daemon=True)
        self.speed_thread.start()

    def _turbo_optimizer_worker(self):
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        rows=[]; confirmations=[]; error=None; final_restore=None; result=None
        started=time.monotonic()
        factors=[10.0,12.0,14.0,16.0,18.0,20.0,24.0,28.0,32.0,36.0,40.0,48.0]
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[TURBO-OPT] Start: sichtbar vs minimiert vs versteckt; Feinsuche danach SICHTBAR.")
                if self.speed_info:
                    ok,_,reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok:
                        print(f"[TURBO-OPT] alter Speed-Kandidat verworfen: {reason}")
                        self.speed_info=None
                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info:
                    raise RuntimeError("Kein gueltiger Same-Session-Speed-Cache; kein Vollscan als Fallback.")
                binding=core.verify_speed_binding_with_f5(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid)
                counters=core.load_same_session_effective_speed_counters(
                    self.hproc,self.pid,self.speed_info,max_count=2
                )
                addresses=list(counters.get("addresses") or [])
                if not addresses:
                    raise RuntimeError("Kein kalibrierter Spielzaehler derselben Anno-Sitzung gefunden.")
                print(f"[TURBO-OPT] Zaehler: {[hex(a) for a in addresses]} aus {counters.get('source_run')}")

                core.restore_game_window_visible(self.hwnd,settle=0.18)
                core.focus_game(self.hwnd,verify=False)
                base=core.measure_effective_counter_cpu_window(
                    self.hproc,self.speed_info,addresses,1.0,duration=0.80,
                    expected_pid=self.pid,stop_event=self.speed_stop
                )
                base_rate=float(base.get("median_rate") or 0)
                if base_rate<=0:
                    raise RuntimeError("1x-Basisrate konnte nicht gemessen werden.")
                base["label"]="1X_VISIBLE_BASE"; rows.append(base)
                print(f"[TURBO-OPT] 1x Basis: {base_rate:.2f}")

                # Direct A/B/C at 32x. Visible is mandatory because the practical Turbo must keep the game usable.
                core.restore_game_window_visible(self.hwnd,settle=0.18)
                core.focus_game(self.hwnd,verify=False)
                visible=core.measure_effective_counter_cpu_window(
                    self.hproc,self.speed_info,addresses,32.0,duration=0.95,
                    expected_pid=self.pid,stop_event=self.speed_stop
                )
                visible_rate=float(visible.get("median_rate") or 0); visible_eff=visible_rate/base_rate if visible_rate>0 else 0
                visible.update({"label":"32X_VISIBLE_AB","window_mode":"visible","effective_vs_1x":visible_eff}); rows.append(visible)

                core.set_game_window_minimized(self.hwnd,True,settle=0.22)
                mini=core.measure_effective_counter_cpu_window(
                    self.hproc,self.speed_info,addresses,32.0,duration=0.95,
                    expected_pid=self.pid,stop_event=self.speed_stop
                )
                mini_rate=float(mini.get("median_rate") or 0); mini_eff=mini_rate/base_rate if mini_rate>0 else 0
                mini.update({"label":"32X_MINIMIZED_AB","window_mode":"minimized","effective_vs_1x":mini_eff}); rows.append(mini)

                core.set_game_window_hidden(self.hwnd,True,settle=0.22)
                hidden=core.measure_effective_counter_cpu_window(
                    self.hproc,self.speed_info,addresses,32.0,duration=0.95,
                    expected_pid=self.pid,stop_event=self.speed_stop
                )
                hidden_rate=float(hidden.get("median_rate") or 0); hidden_eff=hidden_rate/base_rate if hidden_rate>0 else 0
                hidden.update({"label":"32X_HIDDEN_AB","window_mode":"hidden","effective_vs_1x":hidden_eff}); rows.append(hidden)
                mode="visible"
                print(f"[TURBO-OPT] 32x: sichtbar={visible_eff:.2f}x | minimiert={mini_eff:.2f}x | versteckt={hidden_eff:.2f}x")
                print("[TURBO-OPT] Feinsuche wird bewusst SICHTBAR ausgefuehrt, damit Anno nutzbar bleibt.")

                core.restore_game_window_visible(self.hwnd,settle=0.15)
                core.focus_game(self.hwnd,verify=False)

                sweep=[]
                for factor in factors:
                    self._set_status(f"Turbo optimieren: {factor:g}x ({mode}) ...")
                    row=core.measure_effective_counter_cpu_window(
                        self.hproc,self.speed_info,addresses,factor,duration=0.78,
                        expected_pid=self.pid,stop_event=self.speed_stop
                    )
                    rate=float(row.get("median_rate") or 0)
                    eff=rate/base_rate if rate>0 else None
                    row.update({"label":f"{factor:g}X_{mode.upper()}","window_mode":mode,"effective_vs_1x":eff})
                    rows.append(row); sweep.append(row)
                    if eff is not None:
                        print(f"[TURBO-OPT] {factor:g}x {mode}: real={eff:.2f}x | CPU={float(row.get('cpu_core_equivalents') or 0):.2f}")

                valid=[r for r in sweep if r.get("effective_vs_1x") is not None]
                if not valid:
                    raise RuntimeError("Keine gueltigen Turbo-Raten gemessen.")
                valid.sort(key=lambda r:float(r.get("effective_vs_1x") or 0),reverse=True)
                top=valid[:3]
                confirmed=[]
                for cand in top:
                    factor=float(cand["factor"])
                    vals=[float(cand["effective_vs_1x"])]
                    cpu_vals=[float(cand.get("cpu_core_equivalents") or 0)]
                    for rep in range(2):
                        self._set_status(f"Turbo bestaetigen: {factor:g}x {mode} ({rep+1}/2) ...")
                        row=core.measure_effective_counter_cpu_window(
                            self.hproc,self.speed_info,addresses,factor,duration=1.10,
                            expected_pid=self.pid,stop_event=self.speed_stop
                        )
                        rate=float(row.get("median_rate") or 0)
                        eff=rate/base_rate if rate>0 else None
                        row.update({"label":f"CONFIRM_{factor:g}X_{mode.upper()}_{rep+1}","window_mode":mode,"effective_vs_1x":eff})
                        rows.append(row); confirmations.append(row)
                        if eff is not None:
                            vals.append(eff); cpu_vals.append(float(row.get("cpu_core_equivalents") or 0))
                    med=statistics.median(vals)
                    spread=(max(vals)-min(vals))/med if med else 999.0
                    confirmed.append({
                        "factor":factor,"window_mode":mode,"median_effective_vs_1x":med,
                        "spread":spread,"samples":vals,"median_cpu_core_equivalents":statistics.median(cpu_vals)
                    })
                    print(f"[TURBO-OPT] CONFIRM {factor:g}x: median={med:.2f}x | spread={spread:.3f}")
                confirmed.sort(key=lambda x:(-float(x["median_effective_vs_1x"]),float(x["spread"])))
                best=confirmed[0]
                profile={
                    "schema":1,"version":"0.11.10","factor":best["factor"],
                    "window_mode":best["window_mode"],"effective_vs_1x":best["median_effective_vs_1x"],
                    "spread":best["spread"],"cpu_core_equivalents":best["median_cpu_core_equivalents"],
                    "counter_source_run":counters.get("source_run"),
                    "counter_addresses":[hex(a) for a in addresses],
                    "game_pid":self.pid,"created_unix":time.time()
                }
                profile_path=core.save_turbo_profile(profile)
                print(f"[TURBO-OPT] BEST: {best['factor']:g}x / {mode} -> real {best['median_effective_vs_1x']:.2f}x")
                print(f"[TURBO-OPT] Profil gespeichert: {profile_path}")
                result={
                    "version":"0.11.10","kind":"turbo_optimizer","binding":binding,
                    "counter_source_run":counters.get("source_run"),"counter_addresses":[hex(a) for a in addresses],
                    "base_rate":base_rate,"ab":{"visible":visible_eff,"minimized":mini_eff,"hidden":hidden_eff,"chosen_mode":mode},
                    "factors_requested":factors,"rows":rows,"confirmations":confirmed,"best":best,
                    "profile":profile,"profile_path":str(profile_path),"full_memory_scan_used":False,
                    "money_test_used":False,"game_files_modified":False,
                    "elapsed_total_sec":round(time.monotonic()-started,4)
                }
        except InterruptedError as exc:
            error=f"abgebrochen: {exc}"; print(f"[TURBO-OPT] {error}")
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"; print(f"[TURBO-OPT FEHLER] {error}"); traceback.print_exc()
        finally:
            try:
                if self.hproc and self.speed_info:
                    core.set_custom_speed(self.hproc,self.speed_info,1.0); time.sleep(0.08)
            except Exception:
                pass
            try:
                core.restore_game_window_visible(self.hwnd,settle=0.20)
            except Exception:
                pass
            try:
                if self.hproc and self.speed_info:
                    final_restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25
                    )
            except Exception as exc:
                final_restore={"verified":False,"error":str(exc)}
            payload=result or {"version":"0.11.10","kind":"turbo_optimizer","rows":rows,"error":error}
            payload["final_restore_to_1x"]=final_restore
            if error: payload["error"]=error
            try:
                if core.RUN_DIR:
                    (core.RUN_DIR/"turbo_optimizer.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()
            if not self.closing:
                if result and result.get("best"):
                    b=result["best"]
                    msg=(
                        "Turbo-Optimierung beendet.\n\n"
                        f"Fenstermodus: {b.get('window_mode')}\n"
                        f"Beste Einstellung: {b.get('factor'):g}x\n"
                        f"Reale Geschwindigkeit: {b.get('median_effective_vs_1x'):.2f}x\n"
                        f"Streuung: {b.get('spread'):.3f}\n\n"
                        "Profil gespeichert. TURBO SICHTBAR START kann jetzt benutzt werden.\n"
                        f"1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                    )
                else:
                    msg=f"Turbo-Optimierung nicht abgeschlossen.\n\nGrund: {error}\n1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                self.q.put(("turbo_optimizer_result",msg))
            self._set_status("Turbo-Optimierung fertig; 1x wiederhergestellt.")
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

    def start_turbo_best(self):
        if self.busy or self._speed_action_active():
            messagebox.showinfo("Anno 1503", "Es laeuft gerade bereits eine andere Trainer-/Speed-Aktion.")
            return
        profile=core.load_turbo_profile()
        if not profile:
            messagebox.showinfo("Turbo sichtbar", "Noch kein Turbo-Profil vorhanden. Zuerst TURBO OPTIMIEREN ausfuehren.")
            return
        if self.freeze_thread and self.freeze_thread.is_alive():
            messagebox.showinfo("Anno 1503", "Freeze zuerst stoppen.")
            return
        if not self._ensure_game_for_speed():
            messagebox.showinfo("Anno 1503", "Anno starten und Spielstand laden.")
            return
        self.busy=True
        self.speed_stop.clear()
        self._set_speed_buttons(False)
        try:
            self.turbostop_btn.configure(state="normal")
        except Exception:
            pass
        self.speed_thread=threading.Thread(target=self._turbo_best_worker,args=(profile,),daemon=True)
        self.speed_thread.start()

    def stop_turbo_best(self):
        self.speed_stop.set()
        try:
            self.turbostop_btn.configure(state="disabled")
        except Exception:
            pass

    def _turbo_best_worker(self, profile):
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        error=None; restore=None; started=time.monotonic(); samples=0; exact=0
        factor=float(profile.get("factor") or 0); mode=str(profile.get("window_mode") or "minimized")
        try:
            with self.speed_action_lock:
                core.init_run_logging(); sys.stdout=core.Tee(qw,core.RUN_LOG_FILE); sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                if factor<=0: raise RuntimeError("Turbo-Profil enthaelt keinen gueltigen Faktor.")
                if self.speed_info:
                    ok,_,reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok: self.speed_info=None
                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info: raise RuntimeError("Kein gueltiger Same-Session-Speed-Cache.")
                core.verify_speed_binding_with_f5(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid)
                if mode=="hidden":
                    core.set_game_window_hidden(self.hwnd,True,settle=0.20)
                elif mode=="minimized":
                    core.set_game_window_minimized(self.hwnd,True,settle=0.20)
                else:
                    core.restore_game_window_visible(self.hwnd,settle=0.12)
                    core.focus_game(self.hwnd,verify=False)
                self._set_status(f"TURBO SICHTBAR aktiv: {factor:g}x / {mode} - TURBO STOP zum Beenden")
                print(f"[TURBO SICHTBAR] START {factor:g}x / {mode}")
                while not self.speed_stop.wait(0.05):
                    ok,reason=core.process_identity_ok(self.hproc,self.pid)
                    if not ok: raise RuntimeError(reason)
                    cur=core.read_custom_speed(self.hproc,self.speed_info); samples+=1
                    if cur is not None and abs(float(cur)-factor)<=1e-5: exact+=1
                    if not core.set_custom_speed(self.hproc,self.speed_info,factor):
                        raise RuntimeError("Turbo-Faktor konnte nicht gehalten werden.")
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"; print(f"[TURBO BEST FEHLER] {error}")
        finally:
            try:
                if self.hproc and self.speed_info: core.set_custom_speed(self.hproc,self.speed_info,1.0)
            except Exception: pass
            try: core.restore_game_window_visible(self.hwnd,settle=0.20)
            except Exception: pass
            try:
                if self.hproc and self.speed_info:
                    restore=core.restore_speed_1x_verified(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25)
            except Exception as exc: restore={"verified":False,"error":str(exc)}
            payload={"version":"0.11.10","kind":"turbo_best_session","profile":profile,
                     "elapsed_sec":round(time.monotonic()-started,3),"readback_samples":samples,"exact_samples":exact,
                     "error":error,"final_restore_to_1x":restore}
            try:
                if core.RUN_DIR: (core.RUN_DIR/"turbo_best_session.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
                core.make_result_zip(force=True)
            except Exception: traceback.print_exc()
            if not self.closing:
                self.q.put(("turbo_best_result",f"Turbo sichtbar beendet.\n\n{factor:g}x / {mode}\nLaufzeit: {payload['elapsed_sec']} s\nReadbacks exakt: {exact}/{samples}\n1x Rueckstellung: {'BESTAETIGT' if restore and restore.get('verified') else 'NICHT BESTAETIGT'}"))
            try: self.turbostop_btn.configure(state="disabled")
            except Exception: pass
            self.busy=False; sys.stdout,sys.stderr=oldout,olderr
            self.q.put(("speed_test_done",None))

'''
    g=g.replace(method_anchor,methods+method_anchor,1)

    poll_anchor='''                elif kind == "minimized_turbo_result":\n                    messagebox.showinfo("Mini-Turbo-Kurve", val)\n'''
    if poll_anchor not in g:
        raise RuntimeError('Mini-turbo poll anchor not found')
    g=g.replace(poll_anchor,poll_anchor+'''                elif kind == "turbo_optimizer_result":\n                    messagebox.showinfo("Turbo optimieren", val)\n                elif kind == "turbo_best_result":\n                    messagebox.showinfo("Turbo sichtbar", val)\n''',1)

    gui.write_text(g,encoding='utf-8')
    _replace_exact(updater,'CURRENT_VERSION = "0.11.9"','CURRENT_VERSION = "0.11.10"',1)

    (root/'CHANGELOG_V0_11_10.md').write_text(
        '# V0.11.10 - Turbo Optimizer SICHTBAR\n\n'
        '- Vergleicht 32x sichtbar, minimiert und versteckt.\n'
        '- Feinscan 10x bis 48x bewusst bei sichtbarem Anno-Fenster.\n'
        '- Top-3 Kandidaten werden je zweimal laenger bestaetigt; Auswahl nach Median und Streuung.\n'
        '- Speichert turbo_best_profile.json unter LocalAppData/Anno1503Trainer/profiles.\n'
        '- TURBO SICHTBAR START/STOP nutzt das bestaetigte sichtbare Profil ohne Vollscan.\n'
        '- Kein Geldtest, keine Spieldatei-Aenderung; Stop/Fehler stellt Fenster und 1x wieder her.\n',
        encoding='utf-8'
    )
