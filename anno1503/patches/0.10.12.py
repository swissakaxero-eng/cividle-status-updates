"""Anno 1503 Auto Trainer V0.10.12 - true 16x quick test.

Adds a deliberately short same-session high-speed test. It NEVER falls back to a
full memory scan: cached speed binding must validate live with F5 -> 1.0 or the
quick test aborts. Then 16x is held for five seconds and 1x is restored/verified
in a finally block.
"""
from pathlib import Path

VERSION = "0.10.12"


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

    _replace_exact(core, 'TRAINER_VERSION = "0.10.11"', 'TRAINER_VERSION = "0.10.12"', 1)
    _replace_exact(
        core,
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.11',
        ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.12',
        1,
    )

    g = gui.read_text(encoding="utf-8")
    if "Anno 1503 Auto Trainer V0.10.11 PERMANENT BOOTSTRAP" not in g:
        raise RuntimeError("GUI 0.10.11 title marker not found")
    g = g.replace(
        "Anno 1503 Auto Trainer V0.10.11 PERMANENT BOOTSTRAP",
        "Anno 1503 Auto Trainer V0.10.12 PERMANENT BOOTSTRAP",
    )
    g = g.replace('"version":"0.10.11"', '"version":"0.10.12"')
    g = g.replace(
        "V0.10.11: Session-Cache; Vollscans bei gleicher Anno-Sitzung vermeiden …",
        "V0.10.12: echter 16x-Kurztest ohne Vollscan …",
        1,
    )

    button_anchor = '''        self.combinedtest_btn = ttk.Button(actions, text="SPEED + GELD TEST (CACHE)", command=self.start_combined_test)\n        self.combinedtest_btn.pack(side="left", padx=8)\n'''
    button_new = button_anchor + '''        self.speed16_btn = ttk.Button(actions, text="16x KURZTEST (5s)", command=self.start_speed16_test)\n        self.speed16_btn.pack(side="left", padx=8)\n'''
    if button_anchor not in g:
        raise RuntimeError("Combined-test button anchor not found")
    g = g.replace(button_anchor, button_new, 1)

    state_anchor = '''            self.combinedtest_btn.configure(state=state)\n'''
    if state_anchor not in g:
        raise RuntimeError("Combined-test state anchor not found")
    g = g.replace(
        state_anchor,
        state_anchor + '''            self.speed16_btn.configure(state=state)\n''',
        1,
    )

    method_anchor = '''    # V0108_COMBINED_SPEED_MONEY_TEST\n    def start_combined_test(self):\n'''
    if method_anchor not in g:
        raise RuntimeError("Combined-test method anchor not found")

    methods = r'''    # V01012_TRUE_16X_QUICK_TEST
    def start_speed16_test(self):
        if self.busy or self._speed_action_active():
            messagebox.showinfo("Anno 1503", "Es läuft gerade bereits eine andere Trainer-/Speed-Aktion.")
            return
        if self.freeze_thread and self.freeze_thread.is_alive():
            messagebox.showinfo("Anno 1503", "Freeze zuerst stoppen. 16x-Kurztest und Freeze laufen nicht parallel.")
            return
        if not self._ensure_game_for_speed():
            messagebox.showinfo("Anno 1503", "Anno starten und denselben Spielstand laden.")
            return
        self.busy=True
        self.speed_stop.clear()
        self._set_speed_buttons(False)
        self.speed_thread=threading.Thread(target=self._speed16_worker,daemon=True)
        self.speed_thread.start()

    def _speed16_worker(self):
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        diag=None
        restore_diag=None
        error=None
        started=time.monotonic()
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[16X-KURZTEST] Start: KEIN Vollscan, KEIN Geldtest, Ziel 16x fuer 5 Sekunden.")
                self._set_status("16x-Kurztest: bekannten Speed-Faktor live bestätigen …")

                # Existing in-memory binding may be reused only if still valid.
                if self.speed_info:
                    ok, _, reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok:
                        print(f"[16X-KURZTEST] alter GUI-Kandidat verworfen: {reason}")
                        self.speed_info=None

                # Same-session history is allowed because it is re-proven live by
                # load_same_session_speed_info() with F5 -> 1.0. No full scan here.
                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(
                        self.hproc,self.hwnd,self.pid
                    )
                if not self.speed_info:
                    raise RuntimeError(
                        "Kein gueltiger Same-Session-Speed-Cache. Kurztest bricht ab statt Vollscan zu starten."
                    )

                binding=core.verify_speed_binding_with_f5(
                    self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid
                )
                print(f"[16X-KURZTEST] Bindung bestätigt: {binding}")
                self.q.put(("speed","Speed-Faktor: 16x-Test läuft"))
                self._set_status("16x läuft 5 Sekunden … danach sofort zurück auf 1x.")

                diag=core.sustain_custom_speed_probe(
                    self.hproc,self.speed_info,factor=16.0,duration=5.0,interval=0.05,
                    stop_event=self.speed_stop,expected_pid=self.pid
                )
                print(
                    f"[16X-KURZTEST] 16x beendet: samples={diag.get('samples')} | "
                    f"exakt={diag.get('exact_before_write')} | abweichend={diag.get('overwritten_before_write')}"
                )
        except InterruptedError as exc:
            error=f"abgebrochen: {exc}"
            print(f"[16X-KURZTEST] {error}")
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
            print(f"[16X-KURZTEST FEHLER] {error}")
            traceback.print_exc()
        finally:
            try:
                if self.hproc and self.speed_info:
                    restore_diag=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid
                    )
                elif self.hproc and self.hwnd:
                    core.require_game_focus(self.hwnd,"16x-Kurztest Rückstellung")
                    core.tap(core.VK_F5)
                    time.sleep(0.30)
                    restore_diag={"verified":False,"method":"F5_without_binding","readback":None,
                                  "error":"F5 gesendet; kein Speicher-Readback möglich"}
            except Exception as exc:
                restore_diag={"verified":False,"error":str(exc)}

            payload={
                "version":"0.10.12",
                "kind":"quick_16x_speed_test",
                "target_factor":16.0,
                "requested_duration_sec":5.0,
                "elapsed_total_sec":round(time.monotonic()-started,4),
                "full_memory_scan_used":False,
                "money_test_used":False,
                "speed_probe":diag,
                "restore_to_1x":restore_diag,
                "error":error,
            }
            try:
                if core.RUN_DIR:
                    (core.RUN_DIR/"quick_speed_16x.json").write_text(
                        json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
            except Exception:
                traceback.print_exc()
            try:
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()

            verified=bool(restore_diag and restore_diag.get("verified"))
            if not self.closing:
                if diag:
                    msg=(
                        "16x-Kurztest beendet.\n\n"
                        f"16x-Dauer: {diag.get('actual_elapsed_sec')} s\n"
                        f"Readback-Samples: {diag.get('samples')}\n"
                        f"Davon exakt 16.0: {diag.get('exact_before_write')}\n"
                        f"Abweichungen: {diag.get('overwritten_before_write')}\n"
                        f"1x-Rückstellung: {'BESTÄTIGT' if verified else 'NICHT BESTÄTIGT'}"
                    )
                else:
                    msg=(
                        "16x-Kurztest wurde nicht ausgeführt.\n\n"
                        f"Grund: {error or 'unbekannt'}\n"
                        f"1x-Rückstellung: {'BESTÄTIGT' if verified else 'nicht messbar / nicht bestätigt'}"
                    )
                self.q.put(("speed16_result",msg))
            self._set_status(
                "16x-Kurztest fertig; 1x bestätigt." if verified
                else "16x-Kurztest fertig; 1x-Rückstellung nicht vollständig bestätigt."
            )
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

'''
    g = g.replace(method_anchor, methods + method_anchor, 1)

    poll_anchor = '''        elif kind == "combined_test_result":\n            messagebox.showinfo("Speed + Geld Test", val)\n'''
    if poll_anchor not in g:
        raise RuntimeError("Combined-test poll anchor not found")
    g = g.replace(
        poll_anchor,
        poll_anchor + '''        elif kind == "speed16_result":\n            messagebox.showinfo("16x-Kurztest", val)\n''',
        1,
    )

    # Allow manual custom selection of the newly tested factor as well.
    g = g.replace(
        'values=("0.5","1","2","4","6","8","10"))',
        'values=("0.5","1","2","4","6","8","10","12","16"))',
        1,
    )

    gui.write_text(g,encoding="utf-8")
    _replace_exact(updater,'CURRENT_VERSION = "0.10.11"','CURRENT_VERSION = "0.10.12"',1)

    (root/"CHANGELOG_V0_10_12.md").write_text(
        "# V0.10.12\n\n"
        "- Neuer echter 16x-Kurztest: 5 Sekunden, kein Geldtest, kein Vollscan.\n"
        "- Nur Same-Session-Speed-Cache oder bereits live gueltige GUI-Adresse zulaessig.\n"
        "- Cache-Adresse wird vor 16x erneut per F5 -> 1.0 live bestaetigt.\n"
        "- 16x wird mit bestehender Prozess-/Readback-Ueberwachung gehalten.\n"
        "- finally-Rueckstellung auf 1x mit Readback bleibt Pflicht.\n"
        "- Bei fehlendem Cache Abbruch statt langem Fallback-Vollscan.\n"
        "- Speed-Auswahl um 12x und 16x erweitert.\n",
        encoding="utf-8",
    )
