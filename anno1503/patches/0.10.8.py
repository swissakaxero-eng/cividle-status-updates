"""Anno 1503 Auto Trainer V0.10.8 - restart guardian + combined Speed/Geld test.

- Adds an independent PowerShell restart guardian for post-update relaunch.
- Adds one sequential Speed + Geld diagnostic run with one shared result ZIP.
- Reuses the existing money learner (3x Ctrl+M, exact +500 each round).
- Does not loosen speed calibration thresholds and does not add blind gameplay writes.
"""
from pathlib import Path
import re

VERSION = "0.10.8"


def _advance_version_markers(core: Path, gui: Path, updater: Path):
    c = core.read_text(encoding="utf-8")
    if 'TRAINER_VERSION = "0.10.8"' not in c:
        changed = False
        for old in ("0.10.7", "0.10.6"):
            marker = f'TRAINER_VERSION = "{old}"'
            if marker in c:
                c = c.replace(marker, 'TRAINER_VERSION = "0.10.8"', 1)
                c = c.replace(
                    f' ANNO 1503 HISTORY EDITION - AUTO TRAINER V{old}',
                    ' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.8',
                    1,
                )
                changed = True
                break
        if not changed:
            raise RuntimeError("Core version marker not recognized")
        core.write_text(c, encoding="utf-8")

    g = gui.read_text(encoding="utf-8")
    if "V0.10.8 PERMANENT BOOTSTRAP" not in g:
        changed = False
        for old in ("0.10.7", "0.10.6"):
            marker = f"Anno 1503 Auto Trainer V{old} PERMANENT BOOTSTRAP"
            if marker in g:
                g = g.replace(marker, "Anno 1503 Auto Trainer V0.10.8 PERMANENT BOOTSTRAP")
                changed = True
                break
        if not changed:
            raise RuntimeError("GUI version title marker not recognized")
    g = g.replace('"version":"0.10.7"', '"version":"0.10.8"', 1)
    g = g.replace('"version":"0.10.6"', '"version":"0.10.8"', 1)
    g = g.replace(
        "V0.10.7: Mehrfachtest wird an vorhandene Geld-/Speedlogik angebunden …",
        "V0.10.8: Speed + Geld gemeinsam testen; Update-Neustart doppelt abgesichert …",
        1,
    )
    g = g.replace(
        "V0.10.6: Update-Neustart repariert; Speed-/Spieltests unverändert …",
        "V0.10.8: Speed + Geld gemeinsam testen; Update-Neustart doppelt abgesichert …",
        1,
    )
    gui.write_text(g, encoding="utf-8")

    u = updater.read_text(encoding="utf-8")
    if 'CURRENT_VERSION = "0.10.8"' not in u:
        changed = False
        for old in ("0.10.7", "0.10.6"):
            marker = f'CURRENT_VERSION = "{old}"'
            if marker in u:
                u = u.replace(marker, 'CURRENT_VERSION = "0.10.8"', 1)
                changed = True
                break
        if not changed:
            raise RuntimeError("Updater version marker not recognized")
        updater.write_text(u, encoding="utf-8")


def _patch_restart_guardian(gui: Path):
    text = gui.read_text(encoding="utf-8")
    if "V0108_EXTERNAL_RESTART_GUARDIAN" in text:
        return

    old = '''    def _finish_close_when_safe(self):
        speed_alive=bool(self.speed_thread and self.speed_thread.is_alive())
        freeze_alive=bool(self.freeze_thread and self.freeze_thread.is_alive())
        if speed_alive or freeze_alive:
            self.root.after(75,self._finish_close_when_safe)
            return
        try:
            core.make_result_zip(force=True)
        except Exception:
            pass
        try:
            if self.hproc:
                core.kernel32.CloseHandle(self.hproc)
                self.hproc = None
        except Exception:
            pass
        try:
            core.close_run_logging()
        except Exception:
            pass
        if self.pending_update_script:
            try:
                app_updater.launch_apply_script(self.pending_update_script)
            except Exception as exc:
                try:
                    messagebox.showerror("Anno 1503 Update",f"Updater konnte nicht gestartet werden: {exc}")
                except Exception:
                    pass
        self.root.destroy()
        # V0100_FORCE_EXIT_AFTER_UPDATE_FIX3
        # Nur im Updatepfad den gepackten Prozess wirklich beenden.
        if self.pending_update_script:
            os._exit(0)
'''

    new = '''    def _finish_close_when_safe(self):
        speed_alive=bool(self.speed_thread and self.speed_thread.is_alive())
        freeze_alive=bool(self.freeze_thread and self.freeze_thread.is_alive())
        if speed_alive or freeze_alive:
            self.root.after(75,self._finish_close_when_safe)
            return
        try:
            core.make_result_zip(force=True)
        except Exception:
            pass
        try:
            if self.hproc:
                core.kernel32.CloseHandle(self.hproc)
                self.hproc = None
        except Exception:
            pass
        try:
            core.close_run_logging()
        except Exception:
            pass
        if self.pending_update_script:
            try:
                # V0108_EXTERNAL_RESTART_GUARDIAN
                _exe = os.path.abspath(sys.executable)
                _old_sha = ""
                try:
                    _hashlib = __import__("hashlib")
                    with open(_exe, "rb") as _f:
                        _h = _hashlib.sha256()
                        for _chunk in iter(lambda: _f.read(1024*1024), b""):
                            _h.update(_chunk)
                        _old_sha = _h.hexdigest().lower()
                except Exception:
                    pass

                _base = os.environ.get("LOCALAPPDATA") or os.path.dirname(_exe)
                _gdir = os.path.join(_base, "Anno1503Trainer", "updates")
                os.makedirs(_gdir, exist_ok=True)
                _guard = os.path.join(_gdir, f"restart_guardian_{os.getpid()}.ps1")
                _ps = """param([int]$ParentProcessId,[string]$ExePath,[string]$OldSha)\n$ErrorActionPreference='SilentlyContinue'\n$deadline=(Get-Date).AddSeconds(180)\nwhile((Get-Date)-lt $deadline -and (Get-Process -Id $ParentProcessId -ErrorAction SilentlyContinue)){ Start-Sleep -Milliseconds 200 }\n$changed=$false\nwhile((Get-Date)-lt $deadline){\n  if(Test-Path -LiteralPath $ExePath){\n    try { $sha=(Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash.ToLowerInvariant() } catch { $sha='' }\n    if($sha -and $sha -ne $OldSha){ $changed=$true; break }\n  }\n  Start-Sleep -Milliseconds 500\n}\nif($changed){\n  Start-Sleep -Milliseconds 1200\n  $n=[IO.Path]::GetFileNameWithoutExtension($ExePath)\n  $running=@(Get-Process -Name $n -ErrorAction SilentlyContinue)\n  if($running.Count -eq 0){ Start-Process -FilePath $ExePath -WorkingDirectory ([IO.Path]::GetDirectoryName($ExePath)) }\n}\nRemove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue\n"""
                with open(_guard, "w", encoding="utf-8") as _gf:
                    _gf.write(_ps)

                _env = os.environ.copy()
                for _k in tuple(_env):
                    if _k.startswith("_PYI_") or _k == "_MEIPASS2":
                        _env.pop(_k, None)
                _env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                _sp = __import__("subprocess")
                _flags = (getattr(_sp, "DETACHED_PROCESS", 0) |
                          getattr(_sp, "CREATE_NEW_PROCESS_GROUP", 0) |
                          getattr(_sp, "CREATE_NO_WINDOW", 0))
                _powershell = os.path.join(
                    os.environ.get("SystemRoot", r"C:\\Windows"),
                    "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
                )
                _sp.Popen(
                    [_powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-File", _guard, str(os.getpid()), _exe, _old_sha],
                    env=_env, creationflags=_flags, close_fds=True,
                    stdin=_sp.DEVNULL, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                )
                app_updater.launch_apply_script(self.pending_update_script)
            except Exception as exc:
                try:
                    messagebox.showerror("Anno 1503 Update",f"Updater konnte nicht gestartet werden: {exc}")
                except Exception:
                    pass
        self.root.destroy()
        # V0100_FORCE_EXIT_AFTER_UPDATE_FIX3
        if self.pending_update_script:
            os._exit(0)
'''

    if old not in text:
        raise RuntimeError("GUI close/update block not recognized")
    gui.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_combined_test(gui: Path):
    text = gui.read_text(encoding="utf-8")
    if "V0108_COMBINED_SPEED_MONEY_TEST" in text:
        return

    button_anchor = '''        self.speedcompare_btn = ttk.Button(actions, text="KALIBRIEREN + 6x MESSEN", command=self.start_speed_compare)
        self.speedcompare_btn.pack(side="left", padx=8)
'''
    button_new = button_anchor + '''        self.combinedtest_btn = ttk.Button(actions, text="SPEED + GELD TEST", command=self.start_combined_test)
        self.combinedtest_btn.pack(side="left", padx=8)
'''
    if button_anchor not in text:
        raise RuntimeError("Speed compare button anchor not found")
    text = text.replace(button_anchor, button_new, 1)

    state_anchor = '''            self.speedhack_btn.configure(state=state)
            self.speedcompare_btn.configure(state=state)
            self.start_btn.configure(state=state)
'''
    state_new = '''            self.speedhack_btn.configure(state=state)
            self.speedcompare_btn.configure(state=state)
            self.combinedtest_btn.configure(state=state)
            self.start_btn.configure(state=state)
'''
    if state_anchor not in text:
        raise RuntimeError("Speed button state anchor not found")
    text = text.replace(state_anchor, state_new, 1)

    method_anchor = '''    def start_speedhack_test(self):
'''
    if method_anchor not in text:
        raise RuntimeError("start_speedhack_test anchor not found")

    methods = r'''    # V0108_COMBINED_SPEED_MONEY_TEST
    def start_combined_test(self):
        if self.busy or self._speed_action_active():
            messagebox.showinfo("Anno 1503", "Es läuft gerade bereits eine andere Trainer-/Speed-Aktion.")
            return
        if self.freeze_thread and self.freeze_thread.is_alive():
            messagebox.showinfo("Anno 1503", "Freeze zuerst stoppen. Kombitest und Freeze laufen nicht parallel.")
            return
        if not self._ensure_game_for_speed():
            messagebox.showinfo("Anno 1503", "Anno starten und Spielstand laden, dann erneut testen.")
            return
        self.busy=True
        self.speed_stop.clear()
        self._set_speed_buttons(False)
        self.speed_thread=threading.Thread(target=self._combined_test_worker,daemon=True)
        self.speed_thread.start()

    def _combined_test_worker(self):
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        speed_result=None
        restore_diag=None
        money_diag=None
        errors=[]
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[KOMBITEST] Speed -> bestätigte 1x-Rückstellung -> Geld. Eine Ergebnis-ZIP.")

                self._set_status("Kombitest 1/2: Speed-Adresse prüfen/lernen …")
                try:
                    if self.speed_info:
                        ok, _, reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                        if not ok:
                            print(f"[KOMBITEST] alter Speed-Kandidat verworfen: {reason}")
                            self.speed_info=None
                    if not self.speed_info:
                        self.speed_info=core.learn_speed_factor(
                            self.hproc,self.hwnd,stop_event=self.speed_stop,expected_pid=self.pid
                        )
                    if not self.speed_info:
                        raise RuntimeError("Kein eindeutiger Speed-Faktor gefunden.")
                    self.q.put(("speed","Speed-Faktor: gefunden ✓"))
                    self._set_status("Kombitest 1/2: 1x/2x/4x kalibrieren, danach 6x messen …")
                    speed_result=core.compare_speed_1x_4x_6x(
                        self.hproc,self.hwnd,self.speed_info,
                        stop_event=self.speed_stop,expected_pid=self.pid,phase_duration=2.5
                    )
                except Exception as exc:
                    errors.append(f"speed: {type(exc).__name__}: {exc}")
                    print(f"[KOMBITEST][SPEED FEHLER] {exc}")
                    traceback.print_exc()
                finally:
                    if self.speed_info:
                        try:
                            restore_diag=core.restore_speed_1x_verified(
                                self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid
                            )
                        except Exception as exc:
                            restore_diag={"verified":False,"error":str(exc)}
                    else:
                        try:
                            core.require_game_focus(self.hwnd,"Kombitest Rückstellung 1x")
                            core.tap(core.VK_F5)
                            time.sleep(0.30)
                            restore_diag={"verified":False,"method":"F5_without_binding","readback":None,
                                          "error":"1x gesendet; ohne eindeutige Speed-Adresse kein Speicher-Readback"}
                        except Exception as exc:
                            restore_diag={"verified":False,"error":str(exc)}
                    try:
                        if core.RUN_DIR:
                            (core.RUN_DIR/"combined_speed_restore.json").write_text(
                                json.dumps(restore_diag,indent=2,ensure_ascii=False),encoding="utf-8"
                            )
                    except Exception:
                        traceback.print_exc()
                    print(f"[KOMBITEST] Speed-Rückstellung: {restore_diag}")

                if self.speed_info and not (restore_diag and restore_diag.get("verified")):
                    raise RuntimeError("Kombitest stoppt: 1x-Rückstellung nach Speed nicht bestätigt.")

                self._set_status("Kombitest 2/2: Cheat aktivieren und Geldadresse über 3x +500 prüfen …")
                try:
                    core.auto_select_city_and_enable_cheats(self.hwnd)
                    self.money_addr=core.learn_money(self.hproc,self.hwnd)
                    money_value=core.read_i32(self.hproc,self.money_addr) if self.money_addr else None
                    money_diag={
                        "version":"0.10.8",
                        "method":"existing_learn_money_ctrl_m_3x_plus500",
                        "found":bool(self.money_addr),
                        "address":hex(int(self.money_addr)) if self.money_addr else None,
                        "final_value":money_value,
                        "expected_test_side_effect_gold":1500,
                        "direct_memory_write_used":False,
                        "note":"Bestehende STRG+M-Routine: drei +500-Schritte; kein Kandidat wird blind beschrieben.",
                    }
                    if core.RUN_DIR:
                        (core.RUN_DIR/"money_test_diagnostics.json").write_text(
                            json.dumps(money_diag,indent=2,ensure_ascii=False),encoding="utf-8"
                        )
                    self.q.put(("money","Geld: gefunden ✓" if self.money_addr else "Geld: nicht eindeutig"))
                except Exception as exc:
                    errors.append(f"money: {type(exc).__name__}: {exc}")
                    money_diag={"version":"0.10.8","found":False,"error":str(exc)}
                    print(f"[KOMBITEST][GELD FEHLER] {exc}")
                    traceback.print_exc()
                    try:
                        if core.RUN_DIR:
                            (core.RUN_DIR/"money_test_diagnostics.json").write_text(
                                json.dumps(money_diag,indent=2,ensure_ascii=False),encoding="utf-8"
                            )
                    except Exception:
                        pass

                combo={
                    "version":"0.10.8",
                    "kind":"combined_speed_money_test",
                    "speed":{
                        "completed":bool(speed_result),
                        "calibrated_count":speed_result.get("calibrated_count") if speed_result else None,
                        "stable_6x_count":speed_result.get("stable_6x_count") if speed_result else None,
                        "median_ratio_2x_vs_1x":speed_result.get("median_ratio_2x_vs_1x") if speed_result else None,
                        "median_ratio_4x_vs_1x":speed_result.get("median_ratio_4x_vs_1x") if speed_result else None,
                        "median_ratio_6x_vs_1x_stable":speed_result.get("median_ratio_6x_vs_1x_stable") if speed_result else None,
                        "restore_to_1x":restore_diag,
                    },
                    "money":money_diag,
                    "errors":errors,
                }
                if core.RUN_DIR:
                    (core.RUN_DIR/"combined_test_summary.json").write_text(
                        json.dumps(combo,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
                self._set_status("Kombitest Speed + Geld abgeschlossen. Ergebnis-ZIP wird erstellt …")
                self.q.put(("combined_test_result",
                            "Speed + Geld Test abgeschlossen.\n\n"
                            f"Speed kalibrierte Zähler: {combo['speed']['calibrated_count']}\n"
                            f"Stabile 6x-Zähler: {combo['speed']['stable_6x_count']}\n"
                            f"1x-Rückstellung: {'BESTÄTIGT' if restore_diag and restore_diag.get('verified') else 'F5 gesendet / nicht messbar'}\n"
                            f"Geldadresse: {'GEFUNDEN' if money_diag and money_diag.get('found') else 'NICHT EINDEUTIG'}\n\n"
                            "Hinweis: Der Geldtest benutzt 3x STRG+M und fügt dadurch insgesamt 1500 Gold hinzu."))
        except InterruptedError as exc:
            print(f"[KOMBITEST] {exc}")
            self._set_status("Kombitest abgebrochen; Rückstellungen wurden versucht.")
        except Exception as exc:
            print(f"[KOMBITEST FEHLER] {exc}")
            traceback.print_exc()
            self._set_status(f"Kombitest gestoppt: {exc}")
            if not self.closing:
                self.q.put(("combined_test_result",f"Kombitest gestoppt: {exc}"))
        finally:
            try:
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

'''
    text = text.replace(method_anchor, methods + method_anchor, 1)

    _m = re.search(r'(?m)^(?P<i>[ \t]*)elif kind == "speed_action_done":\n(?P=i)[ \t]+pass\n', text)
    if not _m:
        raise RuntimeError("poll insertion anchor not found")
    _indent = _m.group('i')
    _insert = (
        _indent + 'elif kind == "combined_test_result":\n' +
        _indent + '    messagebox.showinfo("Speed + Geld Test", val)\n' +
        _m.group(0)
    )
    text = text[:_m.start()] + _insert + text[_m.end():]

    gui.write_text(text, encoding="utf-8")


def apply(root):
    root = Path(root)
    core = root / "Anno1503_AutoTrainer.py"
    gui = root / "Anno1503_AutoTrainer_GUI.py"
    updater = root / "updater.py"
    for p in (core, gui, updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    _advance_version_markers(core, gui, updater)
    _patch_restart_guardian(gui)
    _patch_combined_test(gui)

    (root / "CHANGELOG_V0_10_8.md").write_text(
        "# V0.10.8\n\n"
        "- Unabhängiger externer Neustart-Wächter nach Updates.\n"
        "- Wächter wartet auf echten EXE-Austausch und startet nur, wenn noch keine Trainerinstanz läuft.\n"
        "- Neustart-Wächter erhält eine von _PYI_*/_MEIPASS2 bereinigte Umgebung.\n"
        "- Neuer Button SPEED + GELD TEST: Speed-Kalibrierung -> 1x-Rückstellung -> vorhandene Geldsuche -> eine Ergebnis-ZIP.\n"
        "- Geldsuche bleibt die bestehende 3x-STRG+M/+500-Erkennung; keine blinden Geld-Writes.\n"
        "- Speed-Kalibrierungsgrenzen bleiben unverändert.\n",
        encoding="utf-8",
    )
