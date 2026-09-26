"""Anno 1503 Auto Trainer V0.11.7 - targeted Sleep(2) limiter A/B test.

Tests two explicit Sleep(2) loops found by the offline timing scan in AnnoFrame.dll.
Only the in-process immediate byte 2 -> 0 is changed temporarily, with strict
signature checks and unconditional restoration. No game files are modified.
"""
from pathlib import Path

VERSION = "0.11.7"


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
    core=root/'Anno1503_AutoTrainer.py'
    gui=root/'Anno1503_AutoTrainer_GUI.py'
    updater=root/'updater.py'
    for p in (core,gui,updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    _replace_exact(core,'TRAINER_VERSION = "0.11.6"','TRAINER_VERSION = "0.11.7"',1)

    # Module enumeration + safe code-byte patching helpers.
    txt=core.read_text(encoding='utf-8')
    if 'TH32CS_SNAPMODULE = 0x00000008' not in txt:
        _replace_exact(
            core,
            'TH32CS_SNAPPROCESS = 0x00000002\n',
            'TH32CS_SNAPPROCESS = 0x00000002\nTH32CS_SNAPMODULE = 0x00000008\nTH32CS_SNAPMODULE32 = 0x00000010\nPAGE_EXECUTE_READWRITE = 0x40\n',
            1,
        )

    txt=core.read_text(encoding='utf-8')
    if 'class MODULEENTRY32W' not in txt:
        anchor='''class MEMORY_BASIC_INFORMATION(ctypes.Structure):\n'''
        block=r'''class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_ubyte)),
        ("modBaseSize", wt.DWORD),
        ("hModule", wt.HANDLE),
        ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]

'''
        _replace_exact(core,anchor,block+anchor,1)

    txt=core.read_text(encoding='utf-8')
    if 'kernel32.Module32FirstW.argtypes' not in txt:
        anchor='''kernel32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]\n'''
        block='''kernel32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]\nkernel32.Module32FirstW.restype = wt.BOOL\nkernel32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]\nkernel32.Module32NextW.restype = wt.BOOL\n'''
        _replace_exact(core,anchor,anchor+block,1)

    txt=core.read_text(encoding='utf-8')
    if 'kernel32.VirtualProtectEx.argtypes' not in txt:
        anchor='''kernel32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]\n'''
        block='''kernel32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, ctypes.POINTER(wt.DWORD)]\nkernel32.VirtualProtectEx.restype = wt.BOOL\nkernel32.FlushInstructionCache.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t]\nkernel32.FlushInstructionCache.restype = wt.BOOL\n'''
        _replace_exact(core,anchor,anchor+block,1)

    txt=core.read_text(encoding='utf-8')
    if 'def find_remote_module_base(' not in txt:
        anchor='''def open_game(pid):\n'''
        helper=r'''def find_remote_module_base(pid, module_name):
    flags=TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32
    snap=kernel32.CreateToolhelp32Snapshot(flags,int(pid))
    if snap == wt.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot(MODULE) fehlgeschlagen")
    try:
        me=MODULEENTRY32W()
        me.dwSize=ctypes.sizeof(me)
        ok=kernel32.Module32FirstW(snap,ctypes.byref(me))
        wanted=str(module_name).lower()
        while ok:
            if str(me.szModule).lower() == wanted:
                base=int(ctypes.cast(me.modBaseAddr,ctypes.c_void_p).value or 0)
                return {"base":base,"size":int(me.modBaseSize),"path":str(me.szExePath),"name":str(me.szModule)}
            ok=kernel32.Module32NextW(snap,ctypes.byref(me))
    finally:
        kernel32.CloseHandle(snap)
    return None


def patch_process_byte_verified(hproc, addr, expected_byte, replacement_byte):
    addr=int(addr)
    exp=bytes([int(expected_byte)&0xff])
    rep=bytes([int(replacement_byte)&0xff])
    before=read_bytes(hproc,addr,1)
    if before != exp:
        raise RuntimeError(f"Code-Signatur an 0x{addr:X} unerwartet: {before.hex() if before else None} != {exp.hex()}")
    old=wt.DWORD()
    if not kernel32.VirtualProtectEx(hproc,ctypes.c_void_p(addr),1,PAGE_EXECUTE_READWRITE,ctypes.byref(old)):
        raise OSError(ctypes.get_last_error(),"VirtualProtectEx fehlgeschlagen")
    try:
        buf=ctypes.create_string_buffer(rep)
        written=ctypes.c_size_t()
        if not kernel32.WriteProcessMemory(hproc,ctypes.c_void_p(addr),buf,1,ctypes.byref(written)) or written.value != 1:
            raise OSError(ctypes.get_last_error(),"WriteProcessMemory Codebyte fehlgeschlagen")
        kernel32.FlushInstructionCache(hproc,ctypes.c_void_p(addr),1)
    finally:
        dummy=wt.DWORD()
        kernel32.VirtualProtectEx(hproc,ctypes.c_void_p(addr),1,old.value,ctypes.byref(dummy))
    after=read_bytes(hproc,addr,1)
    if after != rep:
        raise RuntimeError(f"Codebyte-Readback an 0x{addr:X} fehlgeschlagen: {after.hex() if after else None}")
    return {"address":hex(addr),"before":exp.hex(),"after":rep.hex(),"old_protect":int(old.value)}


def verify_code_signature(hproc, addr, expected_hex):
    expected=bytes.fromhex(expected_hex)
    got=read_bytes(hproc,int(addr),len(expected))
    return {"ok":got==expected,"address":hex(int(addr)),"expected":expected.hex(),"actual":got.hex() if got else None}


'''
        _replace_exact(core,anchor,helper+anchor,1)

    # GUI: fix missing statistics import from 0.11.6 and add targeted limiter A/B button.
    g=gui.read_text(encoding='utf-8')
    g=g.replace('import os, sys, time, threading, queue, traceback, json',
                'import os, sys, time, threading, queue, traceback, json, statistics',1)

    button_anchor='''        self.effectivespeed_btn.pack(side="left", padx=8)\n'''
    if 'text="LIMITER A/B (Sleep2)"' not in g:
        if button_anchor not in g:
            raise RuntimeError('Effective-speed button anchor missing')
        g=g.replace(button_anchor,button_anchor+'''        self.limiterab_btn = ttk.Button(\n            stress_actions, text="LIMITER A/B (Sleep2)", command=self.start_limiter_ab_test\n        )\n        self.limiterab_btn.pack(side="left", padx=8)\n''',1)

    state_anchor='''            self.effectivespeed_btn.configure(state=state)\n'''
    if 'self.limiterab_btn.configure(state=state)' not in g:
        if state_anchor not in g:
            raise RuntimeError('Effective-speed state anchor missing')
        g=g.replace(state_anchor,state_anchor+'''            self.limiterab_btn.configure(state=state)\n''',1)

    method_anchor='''    # V0116_EFFECTIVE_SPEED_CURVE\n'''
    if 'def start_limiter_ab_test(self):' not in g:
        methods=r'''    # V0117_TARGETED_SLEEP2_LIMITER_AB
    def start_limiter_ab_test(self):
        if self.busy or self._speed_action_active():
            messagebox.showinfo("Anno 1503", "Es laeuft gerade bereits eine andere Trainer-/Speed-Aktion.")
            return
        if self.freeze_thread and self.freeze_thread.is_alive():
            messagebox.showinfo("Anno 1503", "Freeze zuerst stoppen.")
            return
        if not self._ensure_game_for_speed():
            messagebox.showinfo("Anno 1503", "Anno starten und denselben Test-Spielstand laden.")
            return
        ok=messagebox.askyesno(
            "Limiter A/B Test",
            "Kurzer Prozessspeicher-Test an zwei Sleep(2)-Schleifen in AnnoFrame.dll.\n\n"
            "Es werden KEINE Spieldateien geaendert. Jeweils nur ein Immediate-Byte 2 -> 0 im laufenden Prozess, "
            "danach zwingend Rueckstellung.\n\nTest-Spielstand verwenden. Fortfahren?"
        )
        if not ok:
            return
        self.busy=True
        self.speed_stop.clear()
        self._set_speed_buttons(False)
        self.speed_thread=threading.Thread(target=self._limiter_ab_worker,daemon=True)
        self.speed_thread.start()

    def _limiter_ab_worker(self):
        oldout,olderr=sys.stdout,sys.stderr
        qw=QueueWriter(self.q)
        error=None
        final_restore=None
        rows=[]
        patches=[]
        started=time.monotonic()
        A=None; B=None
        try:
            with self.speed_action_lock:
                core.init_run_logging()
                sys.stdout=core.Tee(qw,core.RUN_LOG_FILE)
                sys.stderr=core.Tee(qw,core.RUN_LOG_FILE)
                print("[LIMITER-AB] Teste zwei explizite Sleep(2)-Loops aus dem Offline-Scan. Keine Dateiaenderung.")

                if self.speed_info:
                    ok,_,reason=core.validate_speed_info(self.hproc,self.speed_info,self.pid)
                    if not ok:
                        print(f"[LIMITER-AB] alter Speed-Kandidat verworfen: {reason}")
                        self.speed_info=None
                if not self.speed_info:
                    self.speed_info=core.load_same_session_speed_info(self.hproc,self.hwnd,self.pid)
                if not self.speed_info:
                    raise RuntimeError("Kein gueltiger Same-Session-Speed-Cache; kein Vollscan als Fallback.")
                core.verify_speed_binding_with_f5(self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid)

                counters=core.load_same_session_effective_speed_counters(
                    self.hproc,self.pid,self.speed_info,max_count=2
                )
                addresses=list(counters.get("addresses") or [])
                if not addresses:
                    raise RuntimeError("Keine kalibrierten Spielzaehler derselben Anno-Sitzung gefunden.")

                mod=core.find_remote_module_base(self.pid,"AnnoFrame.dll")
                if not mod or not mod.get("base"):
                    raise RuntimeError("AnnoFrame.dll im laufenden Anno-Prozess nicht gefunden.")
                base=int(mod["base"])
                # Offline scan 2026-09-26:
                # A: RVA 0x3BE1A = B9 02 00 00 00 ; Sleep call at 0x3BE1F
                # B: RVA 0x486C9 = B9 02 00 00 00 ; Sleep call at 0x486CE
                A={"name":"A_3BE1F","instr":base+0x3BE1A,"imm":base+0x3BE1B,
                   "signature":"b9 02 00 00 00 ff 15 63 26 06 00"}
                B={"name":"B_486CE","instr":base+0x486C9,"imm":base+0x486CA,
                   "signature":"b9 02 00 00 00 ff 15 b4 5d 05 00"}
                for p in (A,B):
                    sig=core.verify_code_signature(self.hproc,p["instr"],p["signature"])
                    p["signature_check"]=sig
                    if not sig.get("ok"):
                        raise RuntimeError(f"{p['name']} Signatur stimmt nicht; Test sicher abgebrochen.")
                print(f"[LIMITER-AB] AnnoFrame base={hex(base)}; beide Sleep(2)-Signaturen bestaetigt.")

                def phase(label):
                    self._set_status(f"Limiter A/B: {label} bei 32x ...")
                    reset,ph=core._run_calibration_phase(
                        self.hproc,self.hwnd,self.speed_info,addresses,32.0,0.80,
                        stop_event=self.speed_stop,expected_pid=self.pid
                    )
                    vals=[float(v) for v in (ph.get("rates") or {}).values() if v is not None and float(v)>0]
                    med=statistics.median(vals) if vals else None
                    row={"label":label,"reset":reset,"phase":ph,"median_counter_rate":med}
                    rows.append(row)
                    print(f"[LIMITER-AB] {label}: median_rate={med} rates={ph.get('rates')}")
                    return med

                baseline=phase("ORIGINAL_SLEEP2")

                core.patch_process_byte_verified(self.hproc,A["imm"],0x02,0x00)
                patches.append(A)
                a_rate=phase("A_SLEEP0")
                core.patch_process_byte_verified(self.hproc,A["imm"],0x00,0x02)
                patches.remove(A)

                core.patch_process_byte_verified(self.hproc,B["imm"],0x02,0x00)
                patches.append(B)
                b_rate=phase("B_SLEEP0")
                core.patch_process_byte_verified(self.hproc,B["imm"],0x00,0x02)
                patches.remove(B)

                core.patch_process_byte_verified(self.hproc,A["imm"],0x02,0x00); patches.append(A)
                core.patch_process_byte_verified(self.hproc,B["imm"],0x02,0x00); patches.append(B)
                both_rate=phase("A_PLUS_B_SLEEP0")

                ratios={}
                for key,val in (("A_SLEEP0",a_rate),("B_SLEEP0",b_rate),("A_PLUS_B_SLEEP0",both_rate)):
                    ratios[key]=(float(val)/float(baseline)) if baseline and val else None
                best=max(((v,k) for k,v in ratios.items() if v is not None),default=(None,None))
                print(f"[LIMITER-AB] Verhaeltnisse zu Original: {ratios}; bester={best}")

                result={
                    "version":"0.11.7","kind":"annoFrame_sleep2_limiter_ab",
                    "module":mod,"patch_A":A,"patch_B":B,"rows":rows,
                    "ratios_vs_original":ratios,
                    "best_case":best[1],"best_ratio":best[0],
                    "full_memory_scan_used":False,"money_test_used":False,
                    "game_files_modified":False,
                    "elapsed_total_sec":round(time.monotonic()-started,4),
                }
        except InterruptedError as exc:
            error=f"abgebrochen: {exc}"
            print(f"[LIMITER-AB] {error}")
            result=None
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
            print(f"[LIMITER-AB FEHLER] {error}")
            traceback.print_exc()
            result=None
        finally:
            # Restore any process-code byte still patched, in reverse order.
            for p in list(reversed(patches)):
                try:
                    cur=core.read_bytes(self.hproc,p["imm"],1)
                    if cur == b"\x00":
                        core.patch_process_byte_verified(self.hproc,p["imm"],0x00,0x02)
                    elif cur != b"\x02":
                        print(f"[LIMITER-AB WARNUNG] {p['name']} unerwartetes Byte beim Restore: {cur}")
                except Exception as exc:
                    print(f"[LIMITER-AB RESTORE FEHLER] {p['name']}: {exc}")
            try:
                if self.hproc and self.speed_info:
                    final_restore=core.restore_speed_1x_verified(
                        self.hproc,self.hwnd,self.speed_info,expected_pid=self.pid,settle=0.25
                    )
            except Exception as exc:
                final_restore={"verified":False,"error":str(exc)}

            payload=result or {
                "version":"0.11.7","kind":"annoFrame_sleep2_limiter_ab",
                "full_memory_scan_used":False,"money_test_used":False,
                "game_files_modified":False,"error":error,
                "rows":rows,"elapsed_total_sec":round(time.monotonic()-started,4),
            }
            payload["final_restore_to_1x"]=final_restore
            if error: payload["error"]=error
            try:
                if core.RUN_DIR:
                    (core.RUN_DIR/"limiter_sleep2_ab.json").write_text(
                        json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"
                    )
                core.make_result_zip(force=True)
            except Exception:
                traceback.print_exc()

            if not self.closing:
                if result:
                    ratios=result.get("ratios_vs_original") or {}
                    msg=(
                        "Limiter A/B beendet.\n\n"
                        f"A Sleep(0) / Original: {ratios.get('A_SLEEP0') or 0:.2f}x\n"
                        f"B Sleep(0) / Original: {ratios.get('B_SLEEP0') or 0:.2f}x\n"
                        f"A+B Sleep(0) / Original: {ratios.get('A_PLUS_B_SLEEP0') or 0:.2f}x\n\n"
                        f"Bester Fall: {result.get('best_case')} ({result.get('best_ratio') or 0:.2f}x)\n"
                        f"1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                    )
                else:
                    msg=f"Limiter A/B nicht abgeschlossen.\n\nGrund: {error}\n1x Rueckstellung: {'BESTAETIGT' if final_restore and final_restore.get('verified') else 'NICHT BESTAETIGT'}"
                self.q.put(("limiter_ab_result",msg))
            self._set_status("Limiter A/B fertig; 1x wiederhergestellt." if final_restore and final_restore.get("verified") else "Limiter A/B fertig; Rueckstellung pruefen.")
            sys.stdout,sys.stderr=oldout,olderr
            self.busy=False
            self.q.put(("speed_test_done",None))

'''
        if method_anchor not in g:
            raise RuntimeError('Effective-speed method anchor missing')
        g=g.replace(method_anchor,methods+method_anchor,1)

    poll_anchor='''                elif kind == "speedstress_result":\n                    messagebox.showinfo("Speed-Stresstest", val)\n'''
    if 'elif kind == "limiter_ab_result"' not in g:
        if poll_anchor not in g:
            raise RuntimeError('Stress result poll anchor missing')
        g=g.replace(poll_anchor,poll_anchor+'''                elif kind == "limiter_ab_result":\n                    messagebox.showinfo("Limiter A/B", val)\n''',1)

    gui.write_text(g,encoding='utf-8')
    _replace_exact(updater,'CURRENT_VERSION = "0.11.6"','CURRENT_VERSION = "0.11.7"',1)

    (root/'CHANGELOG_V0_11_7.md').write_text(
        '# V0.11.7 - targeted Sleep(2) limiter A/B\n\n'
        '- Behebt fehlenden statistics-Import im V0.11.6-Auswerter.\n'
        '- Neuer kurzer A/B-Test fuer zwei explizite Sleep(2)-Schleifen aus AnnoFrame.dll.\n'
        '- Strikte Byte-Signaturpruefung vor jedem Patch.\n'
        '- Nur ein Immediate-Byte wird im laufenden Prozess temporaer von 2 auf 0 gesetzt.\n'
        '- Keine Spieldatei wird geaendert; Codebytes werden im finally-Block wiederhergestellt.\n'
        '- Vergleicht reale Spielzaehler-Rate bei 32x: Original, A=Sleep0, B=Sleep0, A+B=Sleep0.\n'
        '- Kein Vollscan, kein Geldtest; finale 1x-Rueckstellung.\n',
        encoding='utf-8'
    )
