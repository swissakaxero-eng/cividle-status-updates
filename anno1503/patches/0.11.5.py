"""Anno 1503 Auto Trainer V0.11.5 - escalating speed stress test + dynamic heading.

Adds a short, same-session speed stress test that escalates from 24x up to 4096x,
stopping at the first process loss, speed readback instability, or failed 1x restore.
No full memory discovery and no money test are used. The main title/heading now
uses app_updater.CURRENT_VERSION so future version headings cannot drift again.
"""
from pathlib import Path

VERSION = "0.11.5"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.11.4"', 'TRAINER_VERSION = "0.11.5"', 1)
    ct = core.read_text(encoding="utf-8")
    if ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.11.4' in ct:
        ct = ct.replace(
            ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.11.4',
            ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.11.5',
            1,
        )
        core.write_text(ct, encoding="utf-8")

    g = gui.read_text(encoding="utf-8")

    # Permanent UI version fix: both title bar and big heading read CURRENT_VERSION.
    if 'self.root.title("Anno 1503 Auto Trainer V0.11.4 PERMANENT BOOTSTRAP")' not in g:
        raise RuntimeError("V0.11.4 root title marker not found")
    g = g.replace(
        'self.root.title("Anno 1503 Auto Trainer V0.11.4 PERMANENT BOOTSTRAP")',
        'self.root.title(f"Anno 1503 Auto Trainer V{app_updater.CURRENT_VERSION} PERMANENT BOOTSTRAP")',
        1,
    )
    if 'ttk.Label(top, text="Anno 1503 Auto Trainer V0.11.3 PERMANENT BOOTSTRAP",' not in g:
        raise RuntimeError("stale V0.11.3 big-heading marker not found")
    g = g.replace(
        'ttk.Label(top, text="Anno 1503 Auto Trainer V0.11.3 PERMANENT BOOTSTRAP",',
        'ttk.Label(top, text=f"Anno 1503 Auto Trainer V{app_updater.CURRENT_VERSION} PERMANENT BOOTSTRAP",',
        1,
    )

    g = g.replace('"version":"0.11.4"', '"version":"0.11.5"')
    g = g.replace('"version": "0.11.4"', '"version": "0.11.5"')
    g = g.replace(
        "V0.11.4: echter 16x-Kurztest ohne Vollscan …",
        "V0.11.5: Speed-Stresstest bis Instabilitaet/Crash + dynamische Versionsanzeige …",
    )

    # Separate second row so the UI does not get wider/cut off.
    share_anchor = '''        share = ttk.LabelFrame(self.root, text="Ergebnis für ChatGPT")\n'''
    if share_anchor not in g:
        raise RuntimeError("share frame anchor not found")
    stress_ui = '''        stress_actions = ttk.Frame(self.root)\n        stress_actions.pack(fill="x", **pad)\n        self.speedstress_btn = ttk.Button(\n            stress_actions, text="STRESS 24x -> 4096x", command=self.start_speed_stress_test\n        )\n        self.speedstress_btn.pack(side="left")\n        ttk.Label(\n            stress_actions,\n            text="stoppt automatisch bei Instabilitaet/Prozessverlust; zwischen Stufen Rueckstellung auf 1x"\n        ).pack(side="left", padx=10)\n\n'''
    g = g.replace(share_anchor, stress_ui + share_anchor, 1)

    state_anchor = '''            self.speed16_btn.configure(state=state)\n'''
    if state_anchor not in g:
        raise RuntimeError("speed16 button state anchor not found")
    g = g.replace(
        state_anchor,
        state_anchor + '''            self.speedstress_btn.configure(state=state)\n''',
        1,
    )

    method_anchor = '''    # V0108_COMBINED_SPEED_MONEY_TEST\n    def start_combined_test(self):\n'''
    if method_anchor not in g:
        raise RuntimeError("combined-test method anchor not found")

    stress_methods = r'''    # V0115_ESCALATING_SPEED_STRESS_TEST
    def start_speed_stress_test(self):
        if self.busy or self._speed_action_active():
            messagebox.showinfo("Anno 1503", "Es laeuft gerade bereits eine andere Trainer-/Speed-Aktion.")
            return
        if self.freeze_thread and self.freeze_thread.is_alive():
            messagebox.showinfo("Anno 1503", "Freeze zuerst stoppen. Stresstest und Freeze laufen nicht parallel.")
            return
        if not messagebox.askyesno(
            "Speed-Stresstest",
            "Dieser Test steigert den Speed automatisch von 24x bis maximal 4096x und kann Anno absichtlich instabil machen oder zum Absturz bringen.\n\n"
            "Bei hohen Faktoren kann sehr viel Spielzeit in wenigen Sekunden vergehen. Bitte einen Test-Spielstand verwenden.\n\n"
            "Fortfahren?"
        ):
            return
        if not self._ensure_game_for_speed():
            messagebox.showinfo("Anno 1503", "Anno starten und denselben Test-Spielstand laden.")
            return
        self.busy=True
        self.speed_stop.clear()
        self._set_speed_buttons(False)
        self.speed_thread=threading.Thread(target=self._speed_stress_worker,daemon=True)
        self.speed_thread.start()

    def _speed_stress_worker(self):
        factors=(24.0,32.0,48.0,64.0,96.0,128.0,192.0,256.0,384.0,512.0,768.0,1024.0,1536.0,2048.0,3072.0,4096.0)
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        stages=[]
        last_stable=None
        stop_factor=None
        stop_reason=None
        process_lost=False
        final_restore=None
        started=time.monotonic()
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[SPEED-STRESS] Start 24x -> 4096x. KEIN Vollscan, KEIN Geldtest.")
                self._set_status("Speed-Stress: bekannten Speed-Faktor live bestaetigen ...")

                if self.speed_info:
                    ok, _, reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok:
                        print(f"[SPEED-STRESS] alter GUI-Kandidat verworfen: {reason}")
                        self.speed_info=None
                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info:
                    raise RuntimeError(
                        "Kein gueltiger Same-Session-Speed-Cache. Stresstest bricht ab statt Vollscan zu starten."
                    )

                binding=core.verify_speed_binding_with_f5(
                    self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid
                )
                print(f"[SPEED-STRESS] Bindung bestaetigt: {binding}")

                for factor in factors:
                    core._raise_if_stopped(self.speed_stop,"Speed-Stress")
                    ok, reason=core.process_identity_ok(self.hproc,self.pid)
                    if not ok:
                        process_lost=True
                        stop_factor=factor
                        stop_reason=reason
                        print(f"[SPEED-STRESS] STOP vor {factor:g}x: {reason}")
                        break

                    # Higher factors need less wall-clock exposure while still giving
                    # enough readbacks to detect process/address instability.
                    duration=1.20 if factor <= 256 else (0.90 if factor <= 1024 else 0.70)
                    self._set_status(f"Speed-Stress: {factor:g}x ({duration:.1f}s) ...")
                    print(f"[SPEED-STRESS] Teste {factor:g}x fuer {duration:.2f}s")
                    stage={"factor":factor,"duration_requested_sec":duration}
                    try:
                        diag=core.sustain_custom_speed_probe(
                            self.hproc,self.speed_info,factor=factor,duration=duration,interval=0.04,
                            stop_event=self.speed_stop,expected_pid=self.pid
                        )
                        stage["probe"]=diag
                        samples=int(diag.get("samples") or 0)
                        exact=int(diag.get("exact_before_write") or 0)
                        overwritten=int(diag.get("overwritten_before_write") or 0)
                        stable=bool(samples >= 5 and exact == samples and overwritten == 0)
                        stage["readback_stable"]=stable
                    except Exception as exc:
                        stage["probe_error"]=f"{type(exc).__name__}: {exc}"
                        stages.append(stage)
                        ok_after, reason_after=core.process_identity_ok(self.hproc,self.pid)
                        process_lost=not ok_after
                        stop_factor=factor
                        stop_reason=stage["probe_error"] if ok_after else reason_after
                        print(f"[SPEED-STRESS] {factor:g}x FEHLER: {stop_reason}")
                        break

                    ok_after, reason_after=core.process_identity_ok(self.hproc,self.pid)
                    stage["process_alive_after_probe"]=bool(ok_after)
                    stage["process_status_after_probe"]=reason_after
                    if not ok_after:
                        stages.append(stage)
                        process_lost=True
                        stop_factor=factor
                        stop_reason=reason_after
                        print(f"[SPEED-STRESS] Prozessverlust bei {factor:g}x: {reason_after}")
                        break

                    restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.20
                    )
                    stage["restore_to_1x"]=restore
                    stages.append(stage)

                    if not stage.get("readback_stable"):
                        stop_factor=factor
                        stop_reason=(
                            f"Readback instabil: samples={samples}, exakt={exact}, abweichend={overwritten}"
                        )
                        print(f"[SPEED-STRESS] STOP {factor:g}x: {stop_reason}")
                        break
                    if not restore.get("verified"):
                        stop_factor=factor
                        stop_reason=f"1x-Rueckstellung nicht bestaetigt: {restore.get('error')}"
                        print(f"[SPEED-STRESS] STOP {factor:g}x: {stop_reason}")
                        break

                    last_stable=factor
                    print(f"[SPEED-STRESS] {factor:g}x STABIL; 1x danach bestaetigt.")
                    time.sleep(0.12)

                if stop_reason is None:
                    stop_reason="Sicherheitsdeckel 4096x erreicht; kein Absturz/keine Instabilitaet erkannt."
                    print(f"[SPEED-STRESS] {stop_reason}")

        except InterruptedError as exc:
            stop_reason=f"abgebrochen: {exc}"
            print(f"[SPEED-STRESS] {stop_reason}")
        except Exception as exc:
            stop_reason=f"{type(exc).__name__}: {exc}"
            print(f"[SPEED-STRESS FEHLER] {stop_reason}")
            traceback.print_exc()
        finally:
            try:
                ok_now, _=core.process_identity_ok(self.hproc,self.pid) if self.hproc else (False,"kein Handle")
                if ok_now and self.speed_info:
                    final_restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25
                    )
                else:
                    final_restore={"verified":False,"error":"Anno-Prozess nicht mehr aktiv; keine 1x-Rueckstellung moeglich."}
            except Exception as exc:
                final_restore={"verified":False,"error":str(exc)}

            payload={
                "version":"0.11.5",
                "kind":"escalating_speed_stress_test",
                "factors":[24,32,48,64,96,128,192,256,384,512,768,1024,1536,2048,3072,4096],
                "full_memory_scan_used":False,
                "money_test_used":False,
                "last_stable_factor":last_stable,
                "stop_factor":stop_factor,
                "stop_reason":stop_reason,
                "process_lost":process_lost,
                "elapsed_total_sec":round(time.monotonic()-started,4),
                "stages":stages,
                "final_restore_to_1x":final_restore,
            }
            try:
                if core.RUN_DIR:
                    (core.RUN_DIR/"speed_stress_to_failure.json").write_text(
                        json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
            except Exception:
                traceback.print_exc()
            try:
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()

            if not self.closing:
                if process_lost:
                    msg=(
                        "Speed-Stresstest beendet: Anno-Prozess wurde verloren / ist abgestuerzt.\n\n"
                        f"Letzte stabile Stufe: {last_stable:g}x\n" if last_stable else
                        "Speed-Stresstest beendet: Anno-Prozess wurde verloren / ist abgestuerzt.\n\nLetzte stabile Stufe: keine\n"
                    )
                    msg += f"Fehlerstufe: {stop_factor:g}x\nGrund: {stop_reason}"
                else:
                    msg=(
                        "Speed-Stresstest beendet.\n\n"
                        f"Letzte stabile Stufe: {last_stable:g}x\n" if last_stable else
                        "Speed-Stresstest beendet.\n\nLetzte stabile Stufe: keine\n"
                    )
                    if stop_factor is not None:
                        msg += f"Stop bei: {stop_factor:g}x\n"
                    msg += f"Grund: {stop_reason}\n"
                    msg += f"Finale 1x-Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                self.q.put(("speedstress_result",msg))

            self._set_status(
                f"Speed-Stress fertig. Letzte stabile Stufe: {last_stable:g}x" if last_stable
                else "Speed-Stress beendet; keine stabile neue Stufe bestaetigt."
            )
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

'''
    g = g.replace(method_anchor, stress_methods + method_anchor, 1)

    poll_anchor = '''                elif kind == "speed16_result":\n                    messagebox.showinfo("16x-Kurztest", val)\n'''
    if poll_anchor not in g:
        raise RuntimeError("speed16 poll anchor not found")
    g = g.replace(
        poll_anchor,
        poll_anchor + '''                elif kind == "speedstress_result":\n                    messagebox.showinfo("Speed-Stresstest", val)\n''',
        1,
    )

    gui.write_text(g, encoding="utf-8")
    _replace_exact(updater, 'CURRENT_VERSION = "0.11.4"', 'CURRENT_VERSION = "0.11.5"', 1)

    (root / "CHANGELOG_V0_11_5.md").write_text(
        "# V0.11.5\n\n"
        "- Versionsanzeige dauerhaft dynamisch aus app_updater.CURRENT_VERSION; Titel/Heading koennen nicht mehr auseinanderlaufen.\n"
        "- Neuer Speed-Stresstest 24x -> 4096x.\n"
        "- Kurze Stufen mit Prozess-, Adress- und Readback-Pruefung; zwischen stabilen Stufen verifizierte 1x-Rueckstellung.\n"
        "- Stoppt beim ersten Prozessverlust, Readback-Fehler oder fehlgeschlagener 1x-Rueckstellung.\n"
        "- Kein Vollscan und kein Geldtest.\n"
        "- Sicherheitsdeckel 4096x; wenn auch das stabil bleibt, kann ein separater Extremblock folgen.\n",
        encoding="utf-8",
    )
