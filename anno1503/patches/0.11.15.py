'''Anno 1503 Auto Trainer V0.11.15 - live visible Turbo speed slider.

Adds a normal day-to-day Turbo speed control (1x..128x). 32x remains the proven
default, but the running visible Turbo can be changed live without restarting.
TURBO STOP still performs the verified 1x restore.
'''
from pathlib import Path

VERSION = "0.11.15"


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

    _replace_exact(core,'TRAINER_VERSION = "0.11.14"','TRAINER_VERSION = "0.11.15"',1)

    g=gui.read_text(encoding="utf-8")

    turbo_buttons='''        self.turbostop_btn = ttk.Button(
            stress_actions, text="TURBO STOP", command=self.stop_turbo_best, state="disabled"
        )
        self.turbostop_btn.pack(side="left", padx=8)
'''
    turbo_controls=turbo_buttons+'''        # V01115_LIVE_TURBO_SLIDER
        turbo_speed_row = ttk.Frame(self.root)
        turbo_speed_row.pack(fill="x", **pad)
        ttk.Label(turbo_speed_row, text="Turbo Speed sichtbar:").pack(side="left")
        self.turbo_runtime_factor = 32.0
        self.turbo_factor_var = tk.DoubleVar(value=32.0)
        self.turbo_factor_text = tk.StringVar(value="32x")
        self.turbo_factor_scale = ttk.Scale(
            turbo_speed_row, from_=1.0, to=128.0, orient="horizontal",
            variable=self.turbo_factor_var, command=self._on_turbo_factor_slider,
            length=360
        )
        self.turbo_factor_scale.pack(side="left", padx=(8,6), fill="x", expand=True)
        ttk.Label(turbo_speed_row, textvariable=self.turbo_factor_text, width=7).pack(side="left")
        ttk.Label(turbo_speed_row, text="32x bewaehrt | live verstellbar 1-128x").pack(side="left", padx=(8,0))
'''
    if turbo_buttons not in g:
        raise RuntimeError("Turbo button anchor not found")
    g=g.replace(turbo_buttons,turbo_controls,1)

    method_anchor='''    def start_turbo_best(self):
'''
    slider_methods=r'''    def _set_turbo_slider_factor(self, factor, persist=False):
        try:
            factor=max(1.0,min(128.0,float(factor)))
            factor=float(int(round(factor)))
        except Exception:
            factor=32.0
        self.turbo_runtime_factor=factor
        try:
            self.turbo_factor_var.set(factor)
            self.turbo_factor_text.set(f"{factor:g}x")
        except Exception:
            pass
        if persist:
            try:
                profile=core.load_turbo_profile() or {}
                profile=dict(profile)
                profile.update({
                    "schema":1,
                    "version":"0.11.15",
                    "factor":factor,
                    "window_mode":"visible",
                    "game_pid":self.pid if self.pid else profile.get("game_pid"),
                    "updated_unix":time.time(),
                    "source":"manual_visible_slider",
                })
                core.save_turbo_profile(profile)
            except Exception:
                pass
        return factor

    def _on_turbo_factor_slider(self, value):
        try:
            factor=max(1.0,min(128.0,float(value)))
            factor=float(int(round(factor)))
        except Exception:
            return
        self.turbo_runtime_factor=factor
        try:
            self.turbo_factor_text.set(f"{factor:g}x")
        except Exception:
            pass

'''
    if method_anchor not in g:
        raise RuntimeError("start_turbo_best anchor not found")
    g=g.replace(method_anchor,slider_methods+method_anchor,1)

    start_anchor='''        profile=core.load_turbo_profile()
        if not profile:
            profile={
                "schema":1,"version":"0.11.14","factor":32.0,
                "window_mode":"visible","effective_vs_1x":9.0,
                "spread":0.0,"cpu_core_equivalents":None,
                "counter_source_run":None,"counter_addresses":[],
                "game_pid":None,"created_unix":time.time(),
                "source":"confirmed_visible_32x_bootstrap"
            }
            core.save_turbo_profile(profile)
'''
    start_new=start_anchor+'''        profile=dict(profile)
        selected=self._set_turbo_slider_factor(
            getattr(self,"turbo_runtime_factor",profile.get("factor") or 32.0),
            persist=True
        )
        profile["factor"]=selected
        profile["window_mode"]="visible"
'''
    if start_anchor not in g:
        raise RuntimeError("Turbo profile start anchor not found")
    g=g.replace(start_anchor,start_new,1)

    stop_anchor='''    def stop_turbo_best(self):
        self.speed_stop.set()
        try:
            self.turbostop_btn.configure(state="disabled")
        except Exception:
            pass
'''
    stop_new='''    def stop_turbo_best(self):
        try:
            self._set_turbo_slider_factor(
                getattr(self,"turbo_runtime_factor",32.0), persist=True
            )
        except Exception:
            pass
        self.speed_stop.set()
        try:
            self.turbostop_btn.configure(state="disabled")
        except Exception:
            pass
'''
    if stop_anchor not in g:
        raise RuntimeError("Turbo stop anchor not found")
    g=g.replace(stop_anchor,stop_new,1)

    worker_factor='''        factor=float(profile.get("factor") or 0); mode=str(profile.get("window_mode") or "minimized")
'''
    worker_factor_new='''        factor=float(getattr(self,"turbo_runtime_factor",profile.get("factor") or 32.0))
        factor=max(1.0,min(128.0,float(int(round(factor)))))
        mode="visible"
'''
    if worker_factor not in g:
        raise RuntimeError("Turbo worker factor anchor not found")
    g=g.replace(worker_factor,worker_factor_new,1)

    loop_anchor='''                while not self.speed_stop.wait(0.05):
                    ok,reason=core.process_identity_ok(self.hproc,self.pid)
                    if not ok: raise RuntimeError(reason)
                    cur=core.read_custom_speed(self.hproc,self.speed_info); samples+=1
                    if cur is not None and abs(float(cur)-factor)<=1e-5: exact+=1
                    if not core.set_custom_speed(self.hproc,self.speed_info,factor):
                        raise RuntimeError("Turbo-Faktor konnte nicht gehalten werden.")
'''
    loop_new='''                while not self.speed_stop.wait(0.05):
                    ok,reason=core.process_identity_ok(self.hproc,self.pid)
                    if not ok:
                        raise RuntimeError(reason)
                    requested=float(getattr(self,"turbo_runtime_factor",factor))
                    requested=max(1.0,min(128.0,float(int(round(requested)))))
                    if abs(requested-factor)>1e-6:
                        factor=requested
                        print(f"[TURBO SICHTBAR] Live-Speed -> {factor:g}x")
                        self._set_status(f"TURBO SICHTBAR aktiv: {factor:g}x - Regler live | TURBO STOP zum Beenden")
                    cur=core.read_custom_speed(self.hproc,self.speed_info)
                    samples+=1
                    if cur is not None and abs(float(cur)-factor)<=1e-5:
                        exact+=1
                    if not core.set_custom_speed(self.hproc,self.speed_info,factor):
                        raise RuntimeError("Turbo-Faktor konnte nicht gehalten werden.")
'''
    if loop_anchor not in g:
        raise RuntimeError("Turbo runtime loop anchor not found")
    g=g.replace(loop_anchor,loop_new,1)

    mode_anchor='''                if mode=="hidden":
                    core.set_game_window_hidden(self.hwnd,True,settle=0.20)
                elif mode=="minimized":
                    core.set_game_window_minimized(self.hwnd,True,settle=0.20)
                else:
                    core.restore_game_window_visible(self.hwnd,settle=0.12)
                    core.focus_game(self.hwnd,verify=False)
'''
    mode_new='''                core.restore_game_window_visible(self.hwnd,settle=0.12)
                core.focus_game(self.hwnd,verify=False)
'''
    if mode_anchor not in g:
        raise RuntimeError("Turbo window mode anchor not found")
    g=g.replace(mode_anchor,mode_new,1)

    g=g.replace('"version":"0.11.14"','"version":"0.11.15"')
    g=g.replace('"version": "0.11.14"','"version": "0.11.15"')
    g=g.replace('payload={"version":"0.11.14","kind":"turbo_best_session","profile":profile,',
                'payload={"version":"0.11.15","kind":"turbo_best_session","profile":profile,',1)
    gui.write_text(g,encoding="utf-8")

    _replace_exact(updater,'CURRENT_VERSION = "0.11.14"','CURRENT_VERSION = "0.11.15"',1)

    (root/"CHANGELOG_V0_11_15.md").write_text(
        "# V0.11.15 - Live Turbo Speed Regler\\n\\n"
        "- Normaler sichtbarer Turbo-Regler von 1x bis 128x; 32x bleibt bewaehrter Standard.\\n"
        "- Regler kann waehrend laufendem TURBO SICHTBAR live veraendert werden.\\n"
        "- Worker uebernimmt den gerundeten Wert im 50-ms-Regelzyklus.\\n"
        "- Letzter gewaehlter Wert wird beim Start/Stop im Turbo-Profil gespeichert.\\n"
        "- Turbo bleibt immer sichtbar; alte minimized/hidden Profilwerte werden fuer den Alltagsmodus ignoriert.\\n"
        "- TURBO STOP behaelt die bestaetigte 1x-Rueckstellung.\\n"
        "- Keine Spieldatei-, Waren- oder Geldlogik geaendert.\\n",
        encoding="utf-8"
    )
