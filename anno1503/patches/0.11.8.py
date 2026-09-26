"""Anno 1503 Auto Trainer V0.11.8 - CPU/render bottleneck A/B.

Measures effective simulation rate and Anno process CPU time at 1x visible,
32x visible, 32x minimized, and 32x visible again. No full scan, no money test,
no game-file changes. Always restores window and 1x in finally.
"""
from pathlib import Path

VERSION = "0.11.8"


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

    _replace_exact(core,'TRAINER_VERSION = "0.11.7"','TRAINER_VERSION = "0.11.8"',1)

    helper_anchor='def load_same_session_effective_speed_counters(hproc, expected_pid, speed_info, max_count=2):\n'
    if 'def get_process_cpu_time_seconds(' not in core.read_text(encoding='utf-8'):
        helpers=r'''def get_process_cpu_time_seconds(hproc):
    """Return kernel+user CPU time for the target process in seconds."""
    creation=wt.FILETIME(); exit_ft=wt.FILETIME(); kernel=wt.FILETIME(); user=wt.FILETIME()
    if not kernel32.GetProcessTimes(
        hproc,ctypes.byref(creation),ctypes.byref(exit_ft),ctypes.byref(kernel),ctypes.byref(user)
    ):
        raise OSError(ctypes.get_last_error(),"GetProcessTimes fehlgeschlagen")
    def ft_value(ft):
        return (int(ft.dwHighDateTime)<<32) | int(ft.dwLowDateTime)
    return (ft_value(kernel)+ft_value(user))/10_000_000.0


def is_window_minimized(hwnd):
    try:
        return bool(user32.IsIconic(hwnd))
    except Exception:
        return False


def set_game_window_minimized(hwnd, minimized=True, settle=0.25):
    if not hwnd:
        raise RuntimeError("Anno-Fensterhandle fehlt")
    if minimized:
        user32.ShowWindow(hwnd,6)  # SW_MINIMIZE
    else:
        user32.ShowWindow(hwnd,9)  # SW_RESTORE
        time.sleep(0.08)
        user32.SetForegroundWindow(hwnd)
    time.sleep(max(0.05,float(settle)))
    return is_window_minimized(hwnd)


def measure_effective_counter_cpu_window(hproc, speed_info, addresses, factor, duration=0.9,
                                         expected_pid=None, stop_event=None):
    """Measure counter rate + CPU time without requiring window focus.

    Intended for visible/minimized A/B after the caller has already selected the
    desired window state. The speed factor is maintained directly in memory.
    """
    factor=float(factor)
    ok,_,reason=validate_speed_info(hproc,speed_info,expected_pid)
    if not ok:
        raise RuntimeError(reason)
    if not set_custom_speed(hproc,speed_info,factor):
        raise RuntimeError(f"Speed {factor:g}x konnte nicht gesetzt werden")
    time.sleep(0.12)
    ok,rb,reason=validate_speed_info(hproc,speed_info,expected_pid,expected_value=factor)
    if not ok:
        raise RuntimeError(f"Speed {factor:g}x Readback fehlgeschlagen: {reason}")

    _raise_if_stopped(stop_event,"CPU/Grafik A/B")
    start={}
    for a in addresses:
        v,t=_timed_read_u32(hproc,a)
        if v is not None:
            start[a]=(v,t)
    cpu0=get_process_cpu_time_seconds(hproc)
    wall0=time.monotonic()
    deadline=wall0+float(duration)
    hold_samples=0; hold_exact=0
    while time.monotonic()<deadline:
        _raise_if_stopped(stop_event,"CPU/Grafik A/B")
        ok,reason=process_identity_ok(hproc,expected_pid)
        if not ok:
            raise RuntimeError(reason)
        cur=read_custom_speed(hproc,speed_info)
        hold_samples+=1
        if cur is not None and abs(float(cur)-factor)<=1e-5:
            hold_exact+=1
        if not set_custom_speed(hproc,speed_info,factor):
            raise RuntimeError(f"Speed {factor:g}x konnte nicht gehalten werden")
        remain=deadline-time.monotonic()
        if remain>0:
            if stop_event is not None:
                if stop_event.wait(min(0.05,remain)):
                    raise InterruptedError("CPU/Grafik A/B abgebrochen")
            else:
                time.sleep(min(0.05,remain))
    wall1=time.monotonic()
    cpu1=get_process_cpu_time_seconds(hproc)

    rates={}
    for a in addresses:
        old=start.get(a)
        if not old:
            continue
        nv,nt=_timed_read_u32(hproc,a)
        if nv is None:
            continue
        ov,ot=old
        dt=max(1e-6,float(nt)-float(ot))
        delta=(int(nv)-int(ov)) & 0xFFFFFFFF
        if delta < 0x80000000 and delta>0:
            rates[a]=float(delta)/dt
    vals=[float(v) for v in rates.values() if v is not None and float(v)>0]
    elapsed=max(1e-6,wall1-wall0)
    cpu_delta=max(0.0,cpu1-cpu0)
    return {
        "factor":factor,
        "readback":float(rb),
        "duration_sec":elapsed,
        "rates":rates,
        "median_rate":statistics.median(vals) if vals else None,
        "cpu_time_delta_sec":cpu_delta,
        "cpu_core_equivalents":cpu_delta/elapsed,
        "cpu_percent_of_one_core":100.0*cpu_delta/elapsed,
        "hold_samples":hold_samples,
        "hold_exact":hold_exact,
    }


'''
        _replace_exact(core,helper_anchor,helpers+helper_anchor,1)

    g=gui.read_text(encoding='utf-8')
    # Add button next to limiter test.
    button_anchor='''        self.limiterab_btn = ttk.Button(\n            stress_actions, text="LIMITER A/B (Sleep2)", command=self.start_limiter_ab_test\n        )\n        self.limiterab_btn.pack(side="left", padx=8)\n'''
    if button_anchor not in g:
        raise RuntimeError('Limiter button anchor not found')
    button_new=button_anchor+'''        self.cpurender_btn = ttk.Button(\n            stress_actions, text="CPU/GRAFIK A/B", command=self.start_cpu_render_test\n        )\n        self.cpurender_btn.pack(side="left", padx=8)\n'''
    g=g.replace(button_anchor,button_new,1)

    state_anchor='''            self.limiterab_btn.configure(state=state)\n'''
    if state_anchor not in g:
        raise RuntimeError('Limiter state anchor not found')
    g=g.replace(state_anchor,state_anchor+'            self.cpurender_btn.configure(state=state)\n',1)

    method_anchor='''    # V0117_TARGETED_SLEEP2_LIMITER_AB\n    def start_limiter_ab_test(self):\n'''
    if method_anchor not in g:
        raise RuntimeError('Limiter method anchor not found')
    methods=r'''    # V0118_CPU_RENDER_AB
    def start_cpu_render_test(self):
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
        self.speed_thread=threading.Thread(target=self._cpu_render_worker,daemon=True)
        self.speed_thread.start()

    def _cpu_render_worker(self):
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        rows=[]; error=None; final_restore=None; result=None
        started=time.monotonic()
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[CPU/GRAFIK A/B] 1x sichtbar -> 32x sichtbar -> 32x minimiert -> 32x sichtbar.")
                if self.speed_info:
                    ok,_,reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok:
                        print(f"[CPU/GRAFIK A/B] alter Speed-Kandidat verworfen: {reason}")
                        self.speed_info=None
                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info:
                    raise RuntimeError("Kein gueltiger Same-Session-Speed-Cache; kein Vollscan als Fallback.")
                binding=core.verify_speed_binding_with_f5(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid)
                counters=core.load_same_session_effective_speed_counters(self.hproc,self.pid,self.speed_info,max_count=2)
                addresses=list(counters.get("addresses") or [])
                if not addresses:
                    raise RuntimeError("Kein kalibrierter Spielzaehler derselben Anno-Sitzung gefunden.")
                print(f"[CPU/GRAFIK A/B] Zaehler: {[hex(a) for a in addresses]} aus {counters.get('source_run')}")

                def measure(label,factor,minimized):
                    core.set_game_window_minimized(self.hwnd,minimized=minimized,settle=0.25)
                    actual_min=core.is_window_minimized(self.hwnd)
                    if not minimized:
                        core.focus_game(self.hwnd,verify=False)
                    self._set_status(f"CPU/Grafik A/B: {label} ...")
                    row=core.measure_effective_counter_cpu_window(
                        self.hproc,self.speed_info,addresses,factor,duration=0.95,
                        expected_pid=self.pid,stop_event=self.speed_stop
                    )
                    row["label"]=label
                    row["requested_minimized"]=bool(minimized)
                    row["actual_minimized"]=bool(actual_min)
                    rows.append(row)
                    print(
                        f"[CPU/GRAFIK A/B] {label}: rate={row.get('median_rate')} | "
                        f"CPU={row.get('cpu_core_equivalents'):.3f} core | minimized={actual_min}"
                    )
                    return row

                base=measure("1X_VISIBLE",1.0,False)
                vis=measure("32X_VISIBLE",32.0,False)
                mini=measure("32X_MINIMIZED",32.0,True)
                vis2=measure("32X_VISIBLE_AGAIN",32.0,False)

                base_rate=float(base.get("median_rate") or 0)
                vis_rate=float(vis.get("median_rate") or 0)
                mini_rate=float(mini.get("median_rate") or 0)
                vis2_rate=float(vis2.get("median_rate") or 0)
                visible_ref=statistics.median([x for x in (vis_rate,vis2_rate) if x>0]) if (vis_rate>0 or vis2_rate>0) else None
                eff_visible=(visible_ref/base_rate) if visible_ref and base_rate else None
                eff_min=(mini_rate/base_rate) if mini_rate and base_rate else None
                mini_gain=(mini_rate/visible_ref) if mini_rate and visible_ref else None
                vis_cpu=statistics.median([
                    float(x.get("cpu_core_equivalents") or 0) for x in (vis,vis2)
                ])
                mini_cpu=float(mini.get("cpu_core_equivalents") or 0)

                if mini_gain is not None and mini_gain >= 1.15:
                    interpretation="render_or_presentation_bound"
                elif vis_cpu >= 0.85:
                    interpretation="cpu_simulation_bound_likely"
                else:
                    interpretation="internal_tick_wait_limiter_still_likely"
                result={
                    "version":"0.11.8",
                    "kind":"cpu_render_bottleneck_ab",
                    "binding":binding,
                    "counter_source_run":counters.get("source_run"),
                    "counter_addresses":[hex(a) for a in addresses],
                    "rows":rows,
                    "effective_visible_32x_vs_1x":eff_visible,
                    "effective_minimized_32x_vs_1x":eff_min,
                    "minimized_gain_vs_visible":mini_gain,
                    "visible_cpu_core_equivalents_median":vis_cpu,
                    "minimized_cpu_core_equivalents":mini_cpu,
                    "interpretation":interpretation,
                    "full_memory_scan_used":False,
                    "money_test_used":False,
                    "game_files_modified":False,
                    "elapsed_total_sec":round(time.monotonic()-started,4),
                }
        except InterruptedError as exc:
            error=f"abgebrochen: {exc}"
            print(f"[CPU/GRAFIK A/B] {error}")
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
            print(f"[CPU/GRAFIK A/B FEHLER] {error}")
            traceback.print_exc()
        finally:
            try:
                core.set_game_window_minimized(self.hwnd,minimized=False,settle=0.20)
            except Exception as exc:
                print(f"[CPU/GRAFIK A/B] Fenster-Restore Warnung: {exc}")
            try:
                if self.hproc and self.speed_info:
                    final_restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25
                    )
            except Exception as exc:
                final_restore={"verified":False,"error":str(exc)}
            payload=result or {
                "version":"0.11.8","kind":"cpu_render_bottleneck_ab","rows":rows,
                "error":error,"full_memory_scan_used":False,"money_test_used":False,
                "game_files_modified":False,"elapsed_total_sec":round(time.monotonic()-started,4),
            }
            payload["final_restore_to_1x"]=final_restore
            if error: payload["error"]=error
            try:
                if core.RUN_DIR:
                    (core.RUN_DIR/"cpu_render_ab.json").write_text(
                        json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()
            if not self.closing:
                if result:
                    msg=(
                        "CPU/Grafik A/B beendet.\n\n"
                        f"32x sichtbar effektiv: {(result.get('effective_visible_32x_vs_1x') or 0):.2f}x\n"
                        f"32x minimiert effektiv: {(result.get('effective_minimized_32x_vs_1x') or 0):.2f}x\n"
                        f"Minimiert / sichtbar: {(result.get('minimized_gain_vs_visible') or 0):.2f}x\n"
                        f"CPU sichtbar: {(result.get('visible_cpu_core_equivalents_median') or 0):.2f} Kerne\n"
                        f"CPU minimiert: {(result.get('minimized_cpu_core_equivalents') or 0):.2f} Kerne\n"
                        f"Hinweis: {result.get('interpretation')}\n\n"
                        f"1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                    )
                else:
                    msg=f"CPU/Grafik A/B nicht abgeschlossen.\n\nGrund: {error}\n1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                self.q.put(("cpu_render_result",msg))
            self._set_status("CPU/Grafik A/B fertig; 1x wiederhergestellt." if final_restore and final_restore.get("verified") else "CPU/Grafik A/B fertig; Rueckstellung pruefen.")
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

'''
    g=g.replace(method_anchor,methods+method_anchor,1)

    poll_anchor='''                elif kind == "limiter_ab_result":\n                    messagebox.showinfo("Limiter A/B", val)\n'''
    if poll_anchor not in g:
        raise RuntimeError('Limiter poll anchor not found')
    g=g.replace(poll_anchor,poll_anchor+'                elif kind == "cpu_render_result":\n                    messagebox.showinfo("CPU/Grafik A/B", val)\n',1)

    gui.write_text(g,encoding='utf-8')
    _replace_exact(updater,'CURRENT_VERSION = "0.11.7"','CURRENT_VERSION = "0.11.8"',1)

    (root/'CHANGELOG_V0_11_8.md').write_text(
        '# V0.11.8 - CPU/Grafik A/B\n\n'
        '- Neuer kurzer Bottleneck-Test: 1x sichtbar, 32x sichtbar, 32x minimiert, 32x sichtbar erneut.\n'
        '- Misst echte Spielzaehler-Rate und Prozess-CPU-Zeit (Kernel+User).\n'
        '- Kein Vollscan, kein Geldtest, keine Spieldatei-Aenderung.\n'
        '- Fenster wird am Ende wiederhergestellt; finale 1x-Rueckstellung mit Readback.\n'
        '- Interpretation trennt Rendering/Praesentation, CPU-Simulation und verbleibenden internen Tick/Wait-Limiter.\n',
        encoding='utf-8'
    )
