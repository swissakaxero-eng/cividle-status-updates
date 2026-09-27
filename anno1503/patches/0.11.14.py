'''Anno 1503 Auto Trainer V0.11.14 - Turbo worker auto-rebind fix.

Fixes the actual TURBO SICHTBAR START worker: after an Anno process restart it
now tries the same-session cache and, on cache miss, automatically relearns the
speed binding once before starting the visible Turbo profile. No game-file changes.
'''
from pathlib import Path

VERSION = "0.11.14"


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
    for q in (core,gui,updater):
        if not q.is_file():
            raise RuntimeError(f"Required source file missing: {q}")

    _replace_exact(core,'TRAINER_VERSION = "0.11.13"','TRAINER_VERSION = "0.11.14"',1)

    g=gui.read_text(encoding="utf-8")

    old_worker_rebind='''                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info: raise RuntimeError("Kein gueltiger Same-Session-Speed-Cache.")
                core.verify_speed_binding_with_f5(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid)
'''
    new_worker_rebind='''                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info:
                    print("[TURBO SICHTBAR] Neue Anno-Sitzung: Speed-Bindung wird einmal automatisch neu gelernt.")
                    self._set_status("Turbo sichtbar initialisieren: Speed-Bindung einmalig neu lernen ...")
                    self.speed_info=core.learn_speed_factor(
                        self.hproc,self.hwnd,stop_event=self.speed_stop,expected_pid=self.pid
                    )
                if not self.speed_info:
                    raise RuntimeError("Speed-Bindung konnte fuer die aktuelle Anno-Sitzung nicht gelernt werden.")
                core.verify_speed_binding_with_f5(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid)
'''
    if old_worker_rebind not in g:
        raise RuntimeError("Turbo-best worker rebind anchor not found")
    g=g.replace(old_worker_rebind,new_worker_rebind,1)

    old_final='''            try:
                if self.hproc and self.speed_info: core.set_custom_speed(self.hproc,self.speed_info,1.0)
            except Exception: pass
            try: core.restore_game_window_visible(self.hwnd,settle=0.20)
            except Exception: pass
            try:
                if self.hproc and self.speed_info:
                    restore=core.restore_speed_1x_verified(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25)
            except Exception as exc: restore={"verified":False,"error":str(exc)}
'''
    new_final='''            try:
                if self.hproc and self.speed_info:
                    core.set_custom_speed(self.hproc,self.speed_info,1.0)
            except Exception:
                pass
            try:
                core.restore_game_window_visible(self.hwnd,settle=0.20)
            except Exception:
                pass
            try:
                if self.hproc and self.speed_info:
                    restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25
                    )
                elif self.hproc and self.hwnd:
                    core.focus_game(self.hwnd,verify=False)
                    core.tap(core.VK_F5)
                    time.sleep(0.25)
                    restore={
                        "verified":False,
                        "method":"F5_without_binding",
                        "readback":None,
                        "note":"1x per F5 angefordert; ohne Speed-Bindung kein Readback moeglich."
                    }
            except Exception as exc:
                restore={"verified":False,"error":str(exc)}
'''
    if old_final not in g:
        raise RuntimeError("Turbo-best final restore anchor not found")
    g=g.replace(old_final,new_final,1)

    g=g.replace(
        'payload={"version":"0.11.10","kind":"turbo_best_session","profile":profile,',
        'payload={"version":"0.11.14","kind":"turbo_best_session","profile":profile,',
        1
    )
    g=g.replace('"version":"0.11.13"','"version":"0.11.14"')
    g=g.replace('"version": "0.11.13"','"version": "0.11.14"')
    gui.write_text(g,encoding="utf-8")

    _replace_exact(updater,'CURRENT_VERSION = "0.11.13"','CURRENT_VERSION = "0.11.14"',1)

    (root/"CHANGELOG_V0_11_14.md").write_text(
        "# V0.11.14 - Turbo Worker Auto-Rebind Fix\\n\\n"
        "- TURBO SICHTBAR START versucht nach Anno-Neustart zuerst den Same-Session-Cache.\\n"
        "- Bei Cache-Miss wird die Speed-Bindung einmal automatisch neu gelernt.\\n"
        "- Danach startet das gespeicherte sichtbare Turbo-Profil normal.\\n"
        "- Falls Rebind scheitert, wird im Fehlerpfad zumindest F5/1x angefordert.\\n"
        "- Ergebnis-Metadaten auf V0.11.14 korrigiert.\\n"
        "- Keine Spieldatei-, Waren- oder Geldlogik geaendert.\\n",
        encoding="utf-8"
    )
