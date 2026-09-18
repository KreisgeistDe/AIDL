from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
INDEX_PATH=Path("roadmap/v1/index.json")
SCHEMA_PATH=Path("spec/roadmap-v1.schema.json")
OUTPUT_VERSION="aidl.roadmap-output/v1"
TERMINAL_SATISFIED={"complete","not_applicable","excluded","superseded"}
STATUS_ORDER=("open","in_progress","complete","not_applicable","excluded","superseded")
LEGACY_PROJECTIONS={
 "M10":Path("backlog/m9-m10-release-conformance.md"),
 "M10.1":Path("backlog/m10-1-language-freeze.md"),
 "M10.2":Path("backlog/m10-2-m10-3-language-example-migration.md"),
 "M10.3":Path("backlog/m10-2-m10-3-language-example-migration.md"),
}
TODO_PROJECTIONS={"M10.1","M10.2","M10.3"}

def _load(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def _err(code,subject,message): return {"code":code,"subject":subject,"message":message}

def _documents(root:Path):
    errors=[]
    try: schema=_load(root/SCHEMA_PATH); index=_load(root/INDEX_PATH)
    except (OSError,json.JSONDecodeError) as e: return {},[],[_err("ROADMAP-E001",str(INDEX_PATH),str(e))]
    def schema_errors(value,subject):
        return [_err("ROADMAP-E001",subject,f"schema {'.'.join(map(str,x.absolute_path)) or '<root>'}: {x.message}")
                for x in sorted(Draft202012Validator(schema).iter_errors(value),key=lambda x:(list(x.absolute_path),x.message))]
    errors+=schema_errors(index,str(INDEX_PATH)); docs=[]
    if errors:return index,docs,errors
    for entry in index["milestones"]:
        p=Path(entry["path"])
        try:v=_load(root/p)
        except (OSError,json.JSONDecodeError) as e: errors.append(_err("ROADMAP-E007",str(p),str(e)));continue
        errors+=schema_errors(v,str(p)); docs.append((p,v))
    return index,docs,errors

def _link_errors(root:Path,subject:str,link:dict[str,Any]):
    if link["kind"] not in {"path","test","schema"}: return []
    p=Path(link["ref"])
    if p.is_absolute() or ".." in p.parts or not (root/p).is_file():
        return [_err("ROADMAP-E006",subject,f"invalid or missing repository-relative {link['kind']} ref {link['ref']}")]
    return []

def _section(text:str,mid:str)->str:
    m=re.search(r"^##\s+(?:Milestone\s+)?"+re.escape(mid)+r"\b[^\n]*$",text,re.M)
    if not m:return ""
    n=re.search(r"^##\s+(?:Milestone\s+)?M[0-9]",text[m.end():],re.M)
    s=text[m.end():m.end()+n.start() if n else len(text)]
    a=re.search(r"^###\s+.*acceptance criteria\b",s,re.M|re.I)
    return s[:a.start()] if a else s

def _projection_errors(root:Path,m:dict[str,Any]):
    p=m.get("status_projection")
    if not isinstance(p,dict): return []
    path=root/Path(p["path"])
    try:text=path.read_text(encoding="utf-8")
    except OSError as e:return [_err("ROADMAP-E008",p["path"],str(e))]
    errors=[]
    if p["kind"]=="checkbox_order":
        rows=[]
        for line in _section(text,m["id"]).splitlines():
            x=re.match(r"^- \[([ xX])\]\s+\*\*(P[0-2](?:/P[0-2])*)\*\*\s+",line)
            if x:rows.append((x.group(1).lower()=="x",x.group(2).split("/")))
        if len(rows)!=len(m["packages"]):
            return [_err("ROADMAP-E008",p["path"],f"{m['id']} checkbox task count {len(rows)} != JSON package count {len(m['packages'])}")]
        for pkg,(checked,priorities) in zip(m["packages"],rows):
            if checked!=(pkg["status"] in TERMINAL_SATISFIED):errors.append(_err("ROADMAP-E008",p["path"],f"{pkg['id']} checkbox drift from status"))
            if pkg["priority"] not in priorities:errors.append(_err("ROADMAP-E008",p["path"],f"{pkg['id']} priority drift from JSON authority"))
        return errors
    rows=[]
    pattern=re.compile(r"^- \[([ xX])\].*?\b("+re.escape(m["id"])+r"-[0-9]{2})\b",re.M)
    for x in pattern.finditer(text):
        end=text.find("\n",x.start()); line=text[x.start():end if end>=0 else len(text)]
        q=re.search(r"\*\*(P[0-2])\*\*",line)
        rows.append((x.group(2),x.group(1).lower()=="x",q.group(1) if q else None))
    expected=[(x["id"],x["status"] in TERMINAL_SATISFIED,x["priority"]) for x in m["packages"]]
    if [x[0] for x in rows]!=[x[0] for x in expected]:return [_err("ROADMAP-E008",p["path"],f"{m['id']} package IDs/order drift from JSON authority")]
    for actual,want in zip(rows,expected):
        if actual[1]!=want[1]:errors.append(_err("ROADMAP-E008",p["path"],f"{actual[0]} checkbox drift from status"))
        if actual[2] is not None and actual[2]!=want[2]:errors.append(_err("ROADMAP-E008",p["path"],f"{actual[0]} priority drift from JSON authority"))
    return errors

def _legacy_projection(root:Path,m:dict[str,Any]):
    mid=m["id"]; path=LEGACY_PROJECTIONS.get(mid)
    if path is None:return []
    try:text=(root/path).read_text(encoding="utf-8")
    except OSError as e:return [_err("ROADMAP-E008",str(path),str(e))]
    pattern=re.compile(r"^- \[([ xX])\].*?\b("+re.escape(mid)+r"-[0-9]{2})\b",re.M)
    rows=[(x.group(2),x.group(1).lower()=="x") for x in pattern.finditer(text)]
    expected=[(x["id"],x["status"] in TERMINAL_SATISFIED) for x in m["packages"]]
    errors=[]
    if [x[0] for x in rows]!=[x[0] for x in expected]:errors.append(_err("ROADMAP-E008",str(path),f"{mid} package IDs/order drift from JSON authority"))
    else:
        for a,b in zip(rows,expected):
            if a[1]!=b[1]:errors.append(_err("ROADMAP-E008",str(path),f"{a[0]} checkbox drift from status"))
    if mid in TODO_PROJECTIONS:
        try:todo=(root/"TODO.md").read_text(encoding="utf-8")
        except OSError as e:return errors+[_err("ROADMAP-E008","TODO.md",str(e))]
        tr=[(x.group(2),x.group(1).lower()=="x") for x in pattern.finditer(todo)]
        if [x[0] for x in tr]!=[x[0] for x in expected]:errors.append(_err("ROADMAP-E008","TODO.md",f"{mid} package IDs/order drift from JSON authority"))
        else:
            for a,b in zip(tr,expected):
                if a[1]!=b[1]:errors.append(_err("ROADMAP-E008","TODO.md",f"{a[0]} checkbox drift from status"))
    return errors

def _relation_errors(values:dict[str,dict[str,Any]],kind:str):
    errors=[]; edges={k:[] for k in values}
    for k,v in values.items():
        for target in v.get("supersedes",[]):
            if target==k or target not in values:errors.append(_err("ROADMAP-E010",k,f"invalid supersedes reference {target}"))
            else:
                edges[k].append(target)
                if k not in values[target].get("superseded_by",[]):errors.append(_err("ROADMAP-E011",k,f"supersedes {target} without reciprocal superseded_by"))
        for target in v.get("superseded_by",[]):
            if target==k or target not in values:errors.append(_err("ROADMAP-E010",k,f"invalid superseded_by reference {target}"))
            elif k not in values[target].get("supersedes",[]):errors.append(_err("ROADMAP-E011",k,f"superseded_by {target} without reciprocal supersedes"))
    state={};stack=[]
    def visit(k):
        state[k]=1;stack.append(k)
        for t in edges[k]:
            if state.get(t)==1:errors.append(_err("ROADMAP-E012",k,"supersession cycle "+" -> ".join(stack[stack.index(t):]+[t])))
            elif not state.get(t):visit(t)
        stack.pop();state[k]=2
    for k in sorted(edges):
        if not state.get(k):visit(k)
    return errors

def validate_repository(root:Path=ROOT,*,check_markdown:bool=True):
    index,docs,errors=_documents(root)
    if errors:return sorted(errors,key=lambda x:(x["code"],x["subject"],x["message"]))
    entries=index["milestones"]; ids=[x["id"] for x in entries]; auth=index["migration"]["authoritative_milestones"]; pending=index["migration"]["pending_milestones"]; order=index["milestone_order"]
    if ids!=auth:errors.append(_err("ROADMAP-E009",str(INDEX_PATH),"milestone entries must exactly match authoritative_milestones in order"))
    if set(auth)&set(pending) or set(auth)|set(pending)!=set(order):errors.append(_err("ROADMAP-E009",str(INDEX_PATH),"migration scope must partition milestone_order"))
    for label,vals in (("milestone id",ids),("milestone order",[x["order"] for x in entries]),("milestone path",[x["path"] for x in entries])):
        if len(vals)!=len(set(vals)):errors.append(_err("ROADMAP-E002",str(INDEX_PATH),f"duplicate {label}"))
    packages={};owners={};milestones={}
    for path,m in docs:
        milestones[m["id"]]=m; entry=next((x for x in entries if x["path"]==str(path)),None)
        if entry is None or any(m.get(k)!=entry.get(k) for k in ("id","title","order","priority")):errors.append(_err("ROADMAP-E007",str(path),"index/file identity mismatch"))
        if isinstance(m.get("source"),dict):errors+=_link_errors(root,m["id"],m["source"])
        if isinstance(m.get("status_projection"),dict):errors+=_link_errors(root,m["id"],{"kind":"path","ref":m["status_projection"]["path"]})
        seen=set()
        for pkg in m["packages"]:
            pid=pkg["id"]
            if pid in packages:errors.append(_err("ROADMAP-E002",pid,f"duplicate package id; also owned by {owners[pid]}"))
            else:packages[pid]=pkg;owners[pid]=m["id"]
            if pkg["order"] in seen:errors.append(_err("ROADMAP-E002",m["id"],f"duplicate package order {pkg['order']}"))
            seen.add(pkg["order"])
            for link in pkg["evidence"]+pkg["references"]:errors+=_link_errors(root,pid,link)
    if set(milestones)!=set(ids):errors.append(_err("ROADMAP-E007",str(INDEX_PATH),"index milestone set does not match loaded milestone documents"))
    for pid,pkg in packages.items():
        for dep in pkg["depends_on"]:
            if dep==pid:errors.append(_err("ROADMAP-E004",pid,"package cannot depend on itself"))
            elif dep not in packages:errors.append(_err("ROADMAP-E003",pid,f"unknown dependency {dep}"))
    graph={k:[d for d in v["depends_on"] if d in packages and d!=k] for k,v in packages.items()}; state={};stack=[]
    def visit(k):
        state[k]=1;stack.append(k)
        for d in graph[k]:
            if state.get(d)==1:errors.append(_err("ROADMAP-E005",k,"dependency cycle "+" -> ".join(stack[stack.index(d):]+[d])))
            elif not state.get(d):visit(d)
        stack.pop();state[k]=2
    for k in sorted(graph):
        if not state.get(k):visit(k)
    errors+=_relation_errors(packages,"package")+_relation_errors(milestones,"milestone")
    if check_markdown:
        for _,m in docs: errors+=_projection_errors(root,m) if m.get("status_projection") else _legacy_projection(root,m)
    return sorted(errors,key=lambda x:(x["code"],x["subject"],x["message"]))

def load_authority(root:Path=ROOT):
    errors=validate_repository(root)
    if errors:raise ValueError(json.dumps(errors,sort_keys=True))
    index=_load(root/INDEX_PATH); milestones=[];packages={};owners={}
    for e in index["milestones"]:
        m=_load(root/Path(e["path"]));milestones.append(m)
        for p in m["packages"]:packages[p["id"]]=p;owners[p["id"]]=m["id"]
    return index,milestones,packages,owners

def _blocked(pkg,packages):return [d for d in pkg["depends_on"] if packages[d]["status"] not in TERMINAL_SATISFIED]
def _row(pkg,packages,owners):return {"id":pkg["id"],"milestone":owners[pkg["id"]],"status":pkg["status"],"priority":pkg["priority"],"depends_on":pkg["depends_on"],"blocked_by":_blocked(pkg,packages)}

def summary_data(root:Path=ROOT):
    index,ms,packages,owners=load_authority(root); counts={s:0 for s in STATUS_ORDER}
    for p in packages.values():counts[p["status"]]+=1
    return {"schema_version":OUTPUT_VERSION,"milestones":len(ms),"packages":len(packages),"status_counts":counts,"pending_migration":index["migration"]["pending_milestones"]}

def next_data(root:Path=ROOT,milestone:str|None=None):
    _,ms,packages,owners=load_authority(root)
    for m in ms:
        if milestone and m["id"]!=milestone:continue
        for p in sorted(m["packages"],key=lambda x:x["order"]):
            if p["status"] in {"open","in_progress"} and not _blocked(p,packages):return {"schema_version":OUTPUT_VERSION,"next":_row(p,packages,owners)}
    return {"schema_version":OUTPUT_VERSION,"next":None}

def blockers_data(package_id:str,root:Path=ROOT,transitive:bool=False):
    _,_,packages,owners=load_authority(root)
    if package_id not in packages:raise KeyError(package_id)
    seen=set();out=[]
    def add(pid):
        for d in _blocked(packages[pid],packages):
            if d not in seen:
                seen.add(d);out.append(_row(packages[d],packages,owners))
                if transitive:add(d)
    add(package_id)
    return {"schema_version":OUTPUT_VERSION,"package":package_id,"blockers":out}

def completed_data(root:Path=ROOT,milestone:str|None=None):
    _,ms,packages,owners=load_authority(root); rows=[]
    for m in ms:
        if milestone and m["id"]!=milestone:continue
        rows.extend(_row(p,packages,owners) for p in sorted(m["packages"],key=lambda x:x["order"]) if p["status"] in TERMINAL_SATISFIED)
    return {"schema_version":OUTPUT_VERSION,"completed":rows}

def superseded_data(root:Path=ROOT):
    _,ms,packages,owners=load_authority(root)
    return {"schema_version":OUTPUT_VERSION,"packages":[_row(p,packages,owners)|{"superseded_by":p.get("superseded_by",[]),"supersedes":p.get("supersedes",[])} for p in packages.values() if p["status"]=="superseded" or p.get("supersedes") or p.get("superseded_by")],"milestones":[{"id":m["id"],"supersedes":m.get("supersedes",[]),"superseded_by":m.get("superseded_by",[])} for m in ms if m.get("supersedes") or m.get("superseded_by")]}

def context_data(root:Path=ROOT,milestone:str|None=None,limit:int=32):
    _,ms,packages,owners=load_authority(root); rows=[]
    for m in ms:
        if milestone and m["id"]!=milestone:continue
        for p in sorted(m["packages"],key=lambda x:x["order"]):
            if p["status"] not in TERMINAL_SATISFIED:rows.append(_row(p,packages,owners))
    return {"schema_version":OUTPUT_VERSION,"milestone":milestone,"next":next_data(root,milestone)["next"],"open_total":len(rows),"items":rows[:limit],"truncated":len(rows)>limit}

def _emit(v,fmt):
    if fmt=="json":print(json.dumps(v,sort_keys=True,separators=(",",":")))
    else:print(json.dumps(v,indent=2,sort_keys=True))

def main(argv=None):
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    for name in ("validate","summary","next","completed","superseded","context"):
        p=sub.add_parser(name);p.add_argument("--format",choices=("human","json"),default="human")
        if name in {"next","completed","context"}:p.add_argument("--milestone")
        if name=="context":p.add_argument("--limit",type=int,default=32)
    p=sub.add_parser("blockers");p.add_argument("package");p.add_argument("--transitive",action="store_true");p.add_argument("--format",choices=("human","json"),default="human")
    a=ap.parse_args(argv)
    try:
        if a.cmd=="validate":
            errors=validate_repository();v={"schema_version":OUTPUT_VERSION,"valid":not errors,"errors":errors};_emit(v,a.format);return 0 if not errors else 1
        if a.cmd=="summary":v=summary_data()
        elif a.cmd=="next":v=next_data(milestone=a.milestone)
        elif a.cmd=="completed":v=completed_data(milestone=a.milestone)
        elif a.cmd=="superseded":v=superseded_data()
        elif a.cmd=="context":v=context_data(milestone=a.milestone,limit=max(1,a.limit))
        else:v=blockers_data(a.package,transitive=a.transitive)
        _emit(v,a.format);return 0
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as e:
        print(str(e),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
