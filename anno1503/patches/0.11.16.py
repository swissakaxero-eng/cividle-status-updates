"""Anno 1503 Auto Trainer V0.11.16 - fast Turbo rebind.

Adds a fast float32 transition scanner for Turbo session rebinding. Instead of
snapshotting and Python-loop comparing ~0.9 GB twice, it scans 1.0 patterns with
bytes.find(), switches to 2x, then filters only those offsets before the normal
4x/0.5x proof. Turbo uses this fast path after an Anno process restart.
"""
from pathlib import Path

VERSION = "0.11.16"


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

    _replace_exact(core,'TRAINER_VERSION = "0.11.15"','TRAINER_VERSION = "0.11.16"',1)

    c=core.read_text(encoding="utf-8")
    anchor="def learn_speed_factor(hproc, hwnd, stop_event=None, expected_pid=None):\n"
    if 'def learn_speed_factor_fast(' not in c:
        helper=r'''def _scan_f32_one_offsets_fast(hproc, stop_event=None, max_region=64*1024*1024,
                               max_hits=400000):
    """Fast first stage for speed binding."""
    one32=struct.pack("<f",1.0)
    groups=[]
    total=0
    hits=0
    for base,size in enum_regions(hproc):
        _raise_if_stopped(stop_event,"Turbo Speed-Suche")
        if size<=0 or size>int(max_region):
            continue
        b=read_bytes(hproc,base,size)
        if not b:
            continue
        total+=len(b)
        offs=[]
        pos=b.find(one32)
        while pos>=0:
            if ((int(base)+int(pos)) & 3)==0:
                offs.append(int(pos))
                hits+=1
                if hits>=int(max_hits):
                    raise RuntimeError(
                        f"Zu viele 1.0-f32-Kandidaten ({hits}); Fast-Rebind sicher abgebrochen."
                    )
            pos=b.find(one32,pos+1)
        if offs:
            groups.append((int(base),offs))
    return groups,total,hits


def _filter_f32_groups_value(hproc, groups, value, stop_event=None):
    pat=struct.pack("<f",float(value))
    out=set()
    for base,offs in groups:
        _raise_if_stopped(stop_event,"Turbo Speed-Suche")
        if not offs:
            continue
        size=max(offs)+4
        b=read_bytes(hproc,base,size)
        if not b or len(b)<size:
            continue
        for off in offs:
            if b[off:off+4]==pat:
                out.add(base+off)
    return out


def learn_speed_factor_fast(hproc, hwnd, stop_event=None, expected_pid=None):
    """Fast Turbo-only rebind using exact 1x->2x->4x->0.5x proof."""
    print("\n[TURBO FAST-REBIND] schnelle Speed-Bindung")
    speed_info=None
    candidates=set()
    restore_diag=None
    started=time.monotonic()
    try:
        _raise_if_stopped(stop_event,"Turbo Fast-Rebind")
        ok,reason=process_identity_ok(hproc,expected_pid)
        if not ok:
            raise RuntimeError(reason)

        require_game_focus(hwnd,"Turbo Fast-Rebind 1x")
        tap(VK_F5)
        _interruptible_wait(0.22,stop_event)
        groups,total,hits=_scan_f32_one_offsets_fast(hproc,stop_event=stop_event)
        print(
            f"  1x Fastscan: {total/1024/1024:.1f} MiB gelesen | "
            f"{hits} exakte f32=1.0 Treffer"
        )

        require_game_focus(hwnd,"Turbo Fast-Rebind 2x")
        tap(VK_F6)
        _interruptible_wait(0.22,stop_event)
        candidates=_filter_f32_groups_value(hproc,groups,2.0,stop_event=stop_event)
        print(f"  nach F6/2x: {len(candidates)} Kandidat(en)")
        if not candidates:
            return None

        require_game_focus(hwnd,"Turbo Fast-Rebind 4x")
        tap(VK_F7)
        _interruptible_wait(0.22,stop_event)
        candidates={a for a in candidates if read_f32(hproc,a)==4.0}
        print(f"  nach F7/4x: {len(candidates)} Kandidat(en)")
        if not candidates:
            return None

        require_game_focus(hwnd,"Turbo Fast-Rebind 0.5x")
        tap(VK_F8)
        _interruptible_wait(0.22,stop_event)
        candidates={a for a in candidates if read_f32(hproc,a)==0.5}
        print(f"  nach F8/0.5x: {len(candidates)} Kandidat(en)")

        if len(candidates)==1:
            addr=next(iter(candidates))
            speed_info={"addr":addr,"width":4}
            print(
                f"  [OK] Turbo-Speed eindeutig: 0x{addr:X} | "
                f"{time.monotonic()-started:.2f}s"
            )
        elif len(candidates)>1:
            print("  [INFO] Mehrere exakte Fast-Rebind-Kandidaten; keiner wird blind gewaehlt.")
        else:
            print("  [INFO] Kein eindeutiger Fast-Rebind-Kandidat.")
        return speed_info
    finally:
        restore_diag=restore_speed_1x_verified(
            hproc,hwnd,speed_info,expected_pid=expected_pid,settle=0.20
        )
        try:
            if RUN_DIR:
                (RUN_DIR/"speed_fast_rebind.json").write_text(
                    json.dumps({
                        "version":TRAINER_VERSION,
                        "kind":"turbo_fast_speed_rebind",
                        "candidate_count":len(candidates),
                        "candidates":[hex(a) for a in sorted(candidates)[:100]],
                        "found":bool(speed_info),
                        "address":hex(speed_info["addr"]) if speed_info else None,
                        "elapsed_sec":round(time.monotonic()-started,4),
                        "restore_to_1x":restore_diag,
                    },indent=2,ensure_ascii=False),encoding="utf-8"
                )
        except Exception:
            traceback.print_exc()


'''
        if anchor not in c:
            raise RuntimeError("learn_speed_factor anchor not found")
        c=c.replace(anchor,helper+anchor,1)
    core.write_text(c,encoding="utf-8")

    g=gui.read_text(encoding="utf-8")
    old='''                    self.speed_info=core.learn_speed_factor(
                        self.hproc,self.hwnd,stop_event=self.speed_stop,expected_pid=self.pid
                    )
'''
    new='''                    self.speed_info=core.learn_speed_factor_fast(
                        self.hproc,self.hwnd,stop_event=self.speed_stop,expected_pid=self.pid
                    )
'''
    actual=g.count(old)
    if actual<1:
        raise RuntimeError("Turbo auto-rebind call anchor not found")
    g=g.replace(old,new)

    g=g.replace('ttk.Label(turbo_speed_row, text="Turbo Speed sichtbar:").pack(side="left")',
                'ttk.Label(turbo_speed_row, text="Turbo Faktor sichtbar:").pack(side="left")',1)
    g=g.replace('ttk.Label(turbo_speed_row, text="32x bewaehrt | live verstellbar 1-128x").pack(side="left", padx=(8,0))',
                'ttk.Label(turbo_speed_row, text="32x Startwert | echter Speed kann darunter liegen").pack(side="left", padx=(8,0))',1)

    g=g.replace('"version":"0.11.15"','"version":"0.11.16"')
    g=g.replace('"version": "0.11.15"','"version": "0.11.16"')
    g=g.replace('payload={"version":"0.11.15","kind":"turbo_best_session","profile":profile,',
                'payload={"version":"0.11.16","kind":"turbo_best_session","profile":profile,',1)
    gui.write_text(g,encoding="utf-8")

    _replace_exact(updater,'CURRENT_VERSION = "0.11.15"','CURRENT_VERSION = "0.11.16"',1)

    (root/"CHANGELOG_V0_11_16.md").write_text(
        "# V0.11.16 - Fast Turbo Rebind\n\n"
        "- Turbo-Rebind nach Anno-Neustart nutzt schnellen f32-Transitionsscan.\n"
        "- Kein Python-4-Byte-Vergleich ueber ~0.9 GB mehr; bytes.find() sucht 1.0 in C.\n"
        "- Danach nur 2x/4x/0.5x-Filter; Adresse nur bei genau einem Kandidaten akzeptiert.\n"
        "- Alte lange learn_speed_factor-Routine bleibt fuer manuelle Diagnose erhalten.\n"
        "- Turbo-Faktor-Label stellt klar: eingestellter Faktor ist nicht gleich echter Simulationsspeed.\n"
        "- Keine Spieldatei-, Waren- oder Geldlogik geaendert.\n",
        encoding="utf-8"
    )
