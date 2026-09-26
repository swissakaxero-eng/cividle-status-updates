"""Anno 1503 Auto Trainer V0.11.12 - UI cleanup + updater sync hardening.

Hides obsolete diagnostic buttons from the normal UI. Updater now treats GitHub
channel/payload as authoritative when available and ignores stale local OneDrive
patch copies whose SHA256 does not match, falling back to verified remote bytes.
"""
from pathlib import Path

VERSION = "0.11.12"


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

    _replace_exact(core,'TRAINER_VERSION = "0.11.10"','TRAINER_VERSION = "0.11.12"',1)

    g=gui.read_text(encoding='utf-8')
    anchor = '''        ttk.Label(
            stress_actions,
            text="stoppt automatisch bei Instabilitaet/Prozessverlust; zwischen Stufen Rueckstellung auf 1x"
        ).pack(side="left", padx=10)
'''
    cleanup = anchor + '''        # V01112_UI_CLEANUP - diagnostic code stays internal, buttons leave normal UI.
        for _name in (
            "speed16_btn", "speedstress_btn", "effectivespeed_btn",
            "limiterab_btn", "cpurender_btn", "miniturbo_btn",
        ):
            _w=getattr(self,_name,None)
            if _w is not None:
                try:
                    _w.pack_forget()
                except Exception:
                    pass
        try:
            for _w in list(stress_actions.winfo_children()):
                if isinstance(_w, ttk.Label):
                    try:
                        _w.pack_forget()
                    except Exception:
                        pass
        except Exception:
            pass
'''
    if anchor not in g:
        raise RuntimeError('Stress label anchor not found for UI cleanup')
    g=g.replace(anchor,cleanup,1)
    gui.write_text(g,encoding='utf-8')

    u=updater.read_text(encoding='utf-8')
    if 'CURRENT_VERSION = "0.11.10"' not in u:
        raise RuntimeError('Updater 0.11.10 marker missing')
    u=u.replace('CURRENT_VERSION = "0.11.10"','CURRENT_VERSION = "0.11.12"',1)
    if 'UPDATER_VERSION = "3.2.2-transactional-process-drain"' in u:
        u=u.replace('UPDATER_VERSION = "3.2.2-transactional-process-drain"',
                    'UPDATER_VERSION = "3.2.3-remote-authoritative-stale-local-fallback"',1)

    old_load = '''def _load_channel():
    obj = _load_local_channel_obj()
    if obj is None:
        obj = json.loads(_request_bytes(CHANNEL_URL, timeout=8).decode("utf-8"))
    if not isinstance(obj, dict) or obj.get("project") != "Anno 1503 Auto Trainer":
        raise RuntimeError("Ungültiger Anno-1503-Updatekanal")
    return obj
'''
    new_load = '''def _load_channel():
    # GitHub is authoritative when reachable. OneDrive is only an offline fallback.
    # This prevents OneDrive sync lag from exposing an older channel.json.
    obj = None
    remote_error = None
    try:
        remote = json.loads(_request_bytes(CHANNEL_URL, timeout=8).decode("utf-8"))
        if isinstance(remote, dict) and remote.get("project") == "Anno 1503 Auto Trainer":
            obj = remote
    except Exception as exc:
        remote_error = exc
    if obj is None:
        obj = _load_local_channel_obj()
    if not isinstance(obj, dict) or obj.get("project") != "Anno 1503 Auto Trainer":
        if remote_error is not None:
            raise RuntimeError(f"Ungültiger Anno-1503-Updatekanal; Remote-Fehler: {remote_error}")
        raise RuntimeError("Ungültiger Anno-1503-Updatekanal")
    return obj
'''
    if old_load not in u:
        raise RuntimeError('Updater _load_channel anchor missing')
    u=u.replace(old_load,new_load,1)

    old_local = '''def _local_patch_bytes(version, expected_sha=None):
    root = _local_update_channel_root()
    if not root:
        return None
    for p in (
        root / "patches" / f"{version}.patch.txt",
        root / "patches" / f"{version}.py",
    ):
        if not p.is_file():
            continue
        data = p.read_bytes()
        if expected_sha and _sha256_bytes(data) != str(expected_sha).lower():
            raise RuntimeError(f"Lokaler Patch {version} hat falsche SHA256")
        return data
    return None
'''
    new_local = '''def _local_patch_bytes(version, expected_sha=None):
    root = _local_update_channel_root()
    if not root:
        return None
    for p in (
        root / "patches" / f"{version}.patch.txt",
        root / "patches" / f"{version}.py",
    ):
        if not p.is_file():
            continue
        data = p.read_bytes()
        if expected_sha and _sha256_bytes(data) != str(expected_sha).lower():
            # Stale OneDrive copy: ignore it and let stage_update fetch+verify remote.
            continue
        return data
    return None
'''
    if old_local not in u:
        raise RuntimeError('Updater _local_patch_bytes anchor missing')
    u=u.replace(old_local,new_local,1)
    updater.write_text(u,encoding='utf-8')

    (root/'CHANGELOG_V0_11_12.md').write_text(
        '# V0.11.12 - UI Cleanup + Updater Sync Hardening\n\n'
        '- Alte Diagnose-/Testbuttons aus der normalen Oberflaeche ausgeblendet.\n'
        '- GitHub-Channel ist bei vorhandener Verbindung autoritativ; OneDrive nur Offline-Fallback.\n'
        '- Lokale OneDrive-Patches mit falscher SHA256 werden ignoriert statt das Update zu blockieren.\n'
        '- Remote-Payload wird danach weiterhin zwingend gegen SHA256 geprueft.\n'
        '- Keine Aenderung an Waren-, Geld-, Turbo- oder Gameplay-Logik.\n',
        encoding='utf-8'
    )
