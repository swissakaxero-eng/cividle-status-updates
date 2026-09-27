"""Anno 1503 Auto Trainer V0.11.13 - automatic Turbo session rebind.

Turbo no longer hard-fails when the Anno process changed. It first tries the
same-session cache, then automatically relearns the speed binding once if needed.
If no same-session effective counters exist yet, a persistent visible 32x bootstrap
profile is created from the already confirmed benchmark instead of forcing another
long calibration pass.
"""
from pathlib import Path

VERSION = "0.11.13"


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

    _replace_exact(core,'TRAINER_VERSION = "0.11.12"','TRAINER_VERSION = "0.11.13"',1)

    g=gui.read_text(encoding="utf-8")

    old_rebind = '''                if not self.speed_info:\n                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)\n                if not self.speed_info:\n                    raise RuntimeError("Kein gueltiger Same-Session-Speed-Cache; kein Vollscan als Fallback.")\n'''
    new_rebind = '''                if not self.speed_info:\n                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)\n                if not self.speed_info:\n                    print("[TURBO] Neue Anno-Sitzung erkannt; Speed-Bindung wird einmal automatisch neu gelernt.")\n                    self._set_status("Turbo initialisieren: Speed-Bindung einmalig neu lernen ...")\n                    self.speed_info=core.learn_speed_factor(\n                        self.hproc,self.hwnd,stop_event=self.speed_stop,expected_pid=self.pid\n                    )\n                if not self.speed_info:\n                    raise RuntimeError("Speed-Bindung konnte fuer die aktuelle Anno-Sitzung nicht gelernt werden.")\n'''
    if old_rebind not in g:
        raise RuntimeError("Turbo session-rebind anchor not found")
    g=g.replace(old_rebind,new_rebind)

    old_counter = '''                addresses=list(counters.get("addresses") or [])\n                if not addresses:\n                    raise RuntimeError("Kein kalibrierter Spielzaehler derselben Anno-Sitzung gefunden.")\n                print(f"[TURBO-OPT] Zaehler: {[hex(a) for a in addresses]} aus {counters.get('source_run')}")\n'''
    new_counter = '''                addresses=list(counters.get("addresses") or [])\n                if not addresses:\n                    existing=core.load_turbo_profile()\n                    if existing and float(existing.get("factor") or 0)>0:\n                        factor=float(existing.get("factor"))\n                        eff=float(existing.get("effective_vs_1x") or 9.0)\n                        spread=float(existing.get("spread") or 0.0)\n                        print(f"[TURBO-OPT] Kein neuer Zaehlercache; vorhandenes Profil {factor:g}x sichtbar wird weiterverwendet.")\n                    else:\n                        factor=32.0\n                        eff=9.0\n                        spread=0.0\n                        existing={\n                            "schema":1,"version":"0.11.13","factor":factor,\n                            "window_mode":"visible","effective_vs_1x":eff,\n                            "spread":spread,"cpu_core_equivalents":None,\n                            "counter_source_run":None,"counter_addresses":[],\n                            "game_pid":self.pid,"created_unix":time.time(),\n                            "source":"confirmed_visible_32x_bootstrap"\n                        }\n                        core.save_turbo_profile(existing)\n                        print("[TURBO-OPT] Frische Sitzung ohne Zaehlercache: bestaetigtes sichtbares 32x-Profil gespeichert.")\n                    result={\n                        "version":"0.11.13","kind":"turbo_optimizer_bootstrap",\n                        "best":{\n                            "factor":factor,"window_mode":"visible",\n                            "median_effective_vs_1x":eff,"spread":spread\n                        },\n                        "profile":existing,\n                        "bootstrap_without_counter_scan":True,\n                        "full_memory_scan_used_for_counters":False,\n                        "money_test_used":False,\n                        "game_files_modified":False,\n                        "elapsed_total_sec":round(time.monotonic()-started,4)\n                    }\n                    return\n                print(f"[TURBO-OPT] Zaehler: {[hex(a) for a in addresses]} aus {counters.get('source_run')}")\n'''
    if old_counter not in g:
        raise RuntimeError("Turbo counter anchor not found")
    g=g.replace(old_counter,new_counter,1)

    old_profile = '''        profile=core.load_turbo_profile()\n        if not profile:\n            messagebox.showinfo("Turbo sichtbar", "Noch kein Turbo-Profil vorhanden. Zuerst TURBO OPTIMIEREN ausfuehren.")\n            return\n'''
    new_profile = '''        profile=core.load_turbo_profile()\n        if not profile:\n            profile={\n                "schema":1,"version":"0.11.13","factor":32.0,\n                "window_mode":"visible","effective_vs_1x":9.0,\n                "spread":0.0,"cpu_core_equivalents":None,\n                "counter_source_run":None,"counter_addresses":[],\n                "game_pid":None,"created_unix":time.time(),\n                "source":"confirmed_visible_32x_bootstrap"\n            }\n            core.save_turbo_profile(profile)\n'''
    if old_profile not in g:
        raise RuntimeError("Turbo profile bootstrap anchor not found")
    g=g.replace(old_profile,new_profile,1)

    g=g.replace('"version":"0.11.12"','"version":"0.11.13"')
    g=g.replace('"version": "0.11.12"','"version": "0.11.13"')
    gui.write_text(g,encoding="utf-8")

    _replace_exact(updater,'CURRENT_VERSION = "0.11.12"','CURRENT_VERSION = "0.11.13"',1)

    (root/"CHANGELOG_V0_11_13.md").write_text(
        "# V0.11.13 - Turbo Auto-Rebind\n\n"
        "- Turbo bindet sich nach einem Anno-Neustart automatisch neu an die aktuelle Speed-Adresse.\n"
        "- Same-Session-Cache bleibt der schnelle Standardpfad.\n"
        "- Bei Cache-Miss wird die bestehende Speed-Lernroutine einmal automatisch ausgefuehrt.\n"
        "- Fehlt danach noch ein aktueller Spielzaehler-Cache, wird kein zweiter langer Scan erzwungen.\n"
        "- Stattdessen wird ein sichtbares 32x-Bootstrap-Profil aus dem bestaetigten Benchmark gespeichert/verwendet.\n"
        "- TURBO SICHTBAR START erzeugt bei fehlendem Profil selbststaendig dieses sichere Startprofil.\n"
        "- Keine Aenderung an Spieldateien, Waren- oder Geldlogik.\n",
        encoding="utf-8"
    )
