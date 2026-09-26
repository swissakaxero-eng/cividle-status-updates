"""Anno 1503 Auto Trainer V0.10.7 recovery-safe context export.

Repairs the first V0.10.7 attempt, which could stop after exporting context if one
UI status text anchor differed. This patch is deliberately recovery-aware: it
accepts a mixed 0.10.6/0.10.7 source tree and normalizes all version markers.
It also exports updater.py context for the next restart-hardening patch.
No gameplay, speed, goods, money or memory-write logic is changed.
"""
from pathlib import Path
import ast
import json
import os
import re

VERSION = "0.10.7"


def _ensure_version(path: Path, old: str, new: str, expected_new_count: int = 1):
    text = path.read_text(encoding="utf-8")
    new_count = text.count(new)
    old_count = text.count(old)
    if new_count == expected_new_count and old_count == 0:
        return
    if old_count == expected_new_count and new_count == 0:
        path.write_text(text.replace(old, new), encoding="utf-8")
        return
    raise RuntimeError(
        f"Unexpected recovery state in {path.name}: old={old_count}, new={new_count}, expected={expected_new_count}"
    )


def _replace_any_once(path: Path, olds, new: str):
    text = path.read_text(encoding="utf-8")
    if text.count(new) == 1 and not any(o in text for o in olds):
        return
    hits=[o for o in olds if text.count(o)==1]
    if len(hits)!=1:
        raise RuntimeError(f"Expected exactly one recoverable anchor in {path.name}; hits={len(hits)}")
    path.write_text(text.replace(hits[0],new,1),encoding="utf-8")


def _share_dir():
    for env in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(env)
        if not value:
            continue
        p = Path(value) / "Anno1503Trainer" / "ChatGPT_Auto"
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    return None


def _node_source(lines, node, max_lines=260):
    start=max(1,int(getattr(node,"lineno",1)))
    end=min(len(lines),int(getattr(node,"end_lineno",start)))
    if end-start+1>max_lines:
        end=start+max_lines-1
    return "\n".join(lines[start-1:end])


def _collect(path: Path):
    text=path.read_text(encoding="utf-8")
    lines=text.splitlines()
    tree=ast.parse(text,filename=path.name)
    keys=("geld","money","waren","goods","test","speed","result","run","learn","lern","update","restart","launch","apply","popen","subprocess")
    defs=[]; selected=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            name=node.name
            defs.append({"name":name,"line":node.lineno,"end_line":getattr(node,"end_lineno",node.lineno)})
            src=_node_source(lines,node)
            low=(name+"\n"+src).lower()
            if any(k in low for k in keys):
                selected.append({"name":name,"line":node.lineno,"end_line":getattr(node,"end_lineno",node.lineno),"source":src})
    context=[]
    rx=re.compile(r"geld|money|waren|goods|test jetzt|test.*start|speed|update|restart|launch|popen|subprocess",re.I)
    hits=[i for i,line in enumerate(lines) if rx.search(line)]
    used=set()
    for i in hits[:180]:
        a=max(0,i-6); b=min(len(lines),i+8); key=(a,b)
        if key in used: continue
        used.add(key)
        context.append({"start_line":a+1,"end_line":b,"text":"\n".join(lines[a:b])})
    return {"file":path.name,"line_count":len(lines),"functions":sorted(defs,key=lambda x:x["line"]),"selected_functions":sorted(selected,key=lambda x:x["line"]),"keyword_context":context}


def apply(root):
    root=Path(root)
    core=root/"Anno1503_AutoTrainer.py"
    gui=root/"Anno1503_AutoTrainer_GUI.py"
    updater=root/"updater.py"
    for p in (core,gui,updater):
        if not p.is_file():
            raise RuntimeError(f"Required source file missing: {p}")

    # Export current recovery state, including updater.py this time.
    share=_share_dir()
    if share is not None:
        report={
            "schema":2,
            "kind":"combined_test_development_context",
            "source_version":"0.10.6_to_0.10.7_recovery",
            "purpose":"Exact existing money/speed/test/updater context for sequential multi-test and restart hardening.",
            "files":[_collect(core),_collect(gui),_collect(updater)],
        }
        (share/"DEV_COMBINED_TEST_CONTEXT_V0107_RECOVERY.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")

    _ensure_version(core,'TRAINER_VERSION = "0.10.6"','TRAINER_VERSION = "0.10.7"',1)
    _ensure_version(core,' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.6',' ANNO 1503 HISTORY EDITION - AUTO TRAINER V0.10.7',1)
    _ensure_version(gui,'Anno 1503 Auto Trainer V0.10.6 PERMANENT BOOTSTRAP','Anno 1503 Auto Trainer V0.10.7 PERMANENT BOOTSTRAP',2)
    _ensure_version(gui,'"version":"0.10.6"','"version":"0.10.7"',1)
    _replace_any_once(
        gui,
        [
            'V0.10.6: Update-Neustart repariert; Speed-/Spieltests unverändert …',
            'V0.10.6: Update-Neustart stabilisiert; Testlogik unverändert …',
        ],
        'V0.10.7: Mehrfachtest wird an vorhandene Geld-/Speedlogik angebunden …'
    )
    _ensure_version(updater,'CURRENT_VERSION = "0.10.6"','CURRENT_VERSION = "0.10.7"',1)

    (root/"CHANGELOG_V0_10_7.md").write_text(
        "# V0.10.7\n\n"
        "- Recovery-sichere Entwicklungsbruecke fuer den Mehrfachtest.\n"
        "- Akzeptiert einen teilweise bearbeiteten 0.10.6/0.10.7-Zwischenstand.\n"
        "- Exportiert jetzt auch updater.py-Kontext fuer Restart-Haertung.\n"
        "- Keine Aenderung an Speed-, Waren-, Geld- oder Gameplay-Schreiblogik.\n",
        encoding="utf-8",
    )
