"""Compiler-owned checks for the declared Core type surface (M10-03)."""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
try:
    from .compiler_project import CompilerProject
except ImportError:  # pragma: no cover
    from compiler_project import CompilerProject

SCALARS=set("string int decimal bool uuid date datetime duration revision email url bytes".split())
STD_TYPES=set("Page PageInput Cursor OperationId PrincipalId SubjectId FieldError FieldErrors ProblemDetails Unit".split())
STD_ERRORS=set("InternalFailure InvalidInput NotAuthenticated NotAuthorized ConcurrentChange IdempotencyMismatch DependencyUnavailable RateLimited".split())
NAME=re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
FIELD=re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)$",re.S)
STRING=re.compile(r'^"([^"\\]*(?:\\.[^"\\]*)*)"$')
API_OP=re.compile(r"^(query|mutation)\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)$")

@dataclass(frozen=True)
class TypeRef:
    kind:str; name:str|None=None; args:tuple["TypeRef",...]=()
@dataclass(frozen=True)
class TypeIssue:
    code:str; message:str; source_path:Path; location:object; subject_kind:str; subject_name:str; expected:str
class TypeSyntaxError(ValueError): pass

def _split(text):
    out=[]; buf=[]; stack=[]; quote=None; close={')':'(',']':'[','}':'{','>':'<'}
    for ch in text:
        if quote:
            buf.append(ch)
            if ch==quote and (len(buf)<2 or buf[-2]!='\\'): quote=None
        elif ch in "\"'": quote=ch; buf.append(ch)
        elif ch in "([{<": stack.append(ch); buf.append(ch)
        elif ch in ")]}>":
            if not stack or stack[-1]!=close[ch]: raise TypeSyntaxError("unbalanced type delimiters")
            stack.pop(); buf.append(ch)
        elif ch==',' and not stack:
            part=''.join(buf).strip()
            if not part: raise TypeSyntaxError("empty type argument")
            out.append(part); buf=[]
        else: buf.append(ch)
    if stack or quote: raise TypeSyntaxError("unclosed type expression")
    if (part:=''.join(buf).strip()): out.append(part)
    return tuple(out)

def _take(tail):
    tail=tail.strip()
    if tail.startswith("ref "):
        p=tail.split(None,2); return "ref "+p[1],p[2] if len(p)>2 else ""
    stack=[]; close={')':'(',']':'[','>':'<'}
    for i,ch in enumerate(tail):
        if ch in "([<": stack.append(ch)
        elif ch in ")]>":
            if stack and stack[-1]==close[ch]: stack.pop()
        elif ch.isspace() and not stack: return tail[:i],tail[i+1:].strip()
    return tail,""

def parse_type(raw):
    text=raw.strip()
    if not text: raise TypeSyntaxError("empty type expression")
    if text.endswith('?'):
        inner=text[:-1].strip()
        if not inner or inner.endswith('?'): raise TypeSyntaxError("nullable requires one non-nullable operand")
        return TypeRef("nullable",args=(parse_type(inner),))
    if text.startswith('['):
        if not text.endswith(']') or not text[1:-1].strip(): raise TypeSyntaxError("list requires one element type")
        return TypeRef("list",args=(parse_type(text[1:-1]),))
    if text.startswith("ref "):
        target=re.sub(r"\s*\.\s*",".",text[4:].strip())
        if not NAME.fullmatch(target): raise TypeSyntaxError("ref requires one entity name")
        return TypeRef("ref",target)
    if (m:=re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.-]*)\s*<(.*)>",text,re.S)):
        name=m.group(1); args=tuple(parse_type(x) for x in _split(m.group(2)))
        if name=="set" and len(args)!=1: raise TypeSyntaxError("set requires one type argument")
        if name=="map" and len(args)!=2: raise TypeSyntaxError("map requires two type arguments")
        if not args: raise TypeSyntaxError("generic type requires arguments")
        return TypeRef(name if name in {"set","map"} else "named",None if name in {"set","map"} else name,args)
    if (m:=re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\(.*\))?",text,re.S)) and m.group(1) in SCALARS: return TypeRef("scalar",m.group(1))
    if text.startswith("enum(") and text.endswith(')'): return TypeRef("scalar","string")
    if text.endswith(".id") and NAME.fullmatch(text[:-3]): return TypeRef("entity-id",text[:-3])
    if NAME.fullmatch(text): return TypeRef("named",text)
    raise TypeSyntaxError(f"invalid Core type expression '{text}'")

def _id(item):
    span=item.declaration.span; return item.document.source_path,span.offset if span else -1

def _resolve(project,source,ref):
    ref=re.sub(r"\s*\.\s*",".",ref); found=[]
    if '.' in ref: found.extend(project.symbol_table.lookup_declarations(ref))
    else:
        mod=source.document.module
        if mod and mod.name: found.extend(project.symbol_table.lookup_declarations(f"{mod.name}.{ref}"))
        for r in project.import_resolutions:
            if r.document is source.document: found.extend(x for x in r.declarations if x.declaration.name==ref)
    out=[]; seen=set()
    for x in found:
        if _id(x) not in seen: seen.add(_id(x)); out.append(x)
    return tuple(out)

def _issue(item,code,msg,expected,loc=None):
    loc=loc or item.declaration.span
    return None if loc is None else TypeIssue(code,msg,item.document.source_path,loc,item.declaration.kind,item.declaration.name or "<unnamed>",expected)

def _map_key(project,item,key):
    if key.kind in {"scalar","entity-id"}: return True
    if key.kind!="named" or key.args: return False
    m=_resolve(project,item,key.name or "")
    return key.name in STD_TYPES or (len(m)==1 and m[0].declaration.kind in {"value","enum","alias","opaque"})

def _check_type(project,item,raw,loc=None):
    try: root=parse_type(raw)
    except TypeSyntaxError as e:
        x=_issue(item,"AIDL-T001",str(e),"well-formed Core type constructor",loc); return [x] if x else []
    out=[]
    def visit(t):
        if t.kind=="ref":
            m=[x for x in _resolve(project,item,t.name or "") if x.declaration.kind=="entity"]
            if len(m)!=1:
                x=_issue(item,"AIDL-T001",f"type '{raw}' must reference exactly one entity; found {len(m)}","owner-local ref resolves to one entity",loc); out.extend([x] if x else [])
        if t.kind=="map" and not _map_key(project,item,t.args[0]):
            x=_issue(item,"AIDL-T001",f"map key in '{raw}' must be scalar or value-like","map<K,V> uses scalar/value K",loc); out.extend([x] if x else [])
        for a in t.args: visit(a)
    visit(root); return out

def _field(node):
    if not node.name or not (m:=FIELD.match(node.name.strip())): return None
    typ,mods=_take(m.group(2)); return m.group(1),typ,mods

def _params(raw):
    raw=raw.strip(); raw=raw[1:-1] if raw.startswith('(') and raw.endswith(')') else raw
    return _split(raw) if raw.strip() else ()

def _literal(text):
    text=text.strip()
    if text=="null": return "null"
    if text in {"true","false"}: return "bool"
    if re.fullmatch(r"-?\d+",text): return "int"
    if re.fullmatch(r"-?\d+\.\d+",text): return "decimal"
    if STRING.fullmatch(text): return "string"

def _signature(project,item):
    out=[]; seen=set(); raw=item.declaration.node.attrs.get("parameters")
    if isinstance(raw,str):
        try: parts=_params(raw)
        except TypeSyntaxError as e:
            x=_issue(item,"AIDL-T002",str(e),"typed operation parameters"); return [x] if x else []
        for part in parts:
            if not (m:=FIELD.match(part)):
                x=_issue(item,"AIDL-T002",f"invalid parameter '{part}'","name: Type"); out.extend([x] if x else []); continue
            name=m.group(1); typ,mods=_take(m.group(2)); out.extend(_check_type(project,item,typ))
            if name in seen:
                x=_issue(item,"AIDL-T002",f"duplicate parameter '{name}'","unique parameter names"); out.extend([x] if x else [])
            seen.add(name)
            if (d:=re.search(r"(?:^|\s)default\s+(.+)$",mods,re.S)) and (actual:=_literal(d.group(1))):
                try: expected=parse_type(typ); base=expected.args[0] if expected.kind=="nullable" else expected
                except TypeSyntaxError: continue
                ok=(actual=="null" and expected.kind=="nullable") or (actual!="null" and base.kind=="scalar" and (actual==base.name or (base.name=="decimal" and actual=="int")))
                if not ok:
                    x=_issue(item,"AIDL-T002",f"default type '{actual}' is not assignable to '{typ}'","exact match or implicit int to decimal only"); out.extend([x] if x else [])
    returns=item.declaration.node.attrs.get("returns")
    if isinstance(returns,str) and returns.strip(): out.extend(_check_type(project,item,returns.strip()))
    return out

def _clauses(item,key):
    p=re.compile(rf"^{re.escape(key)}(?:\s*:\s*|\s+)(.*)$",re.S); out=[]
    for n in item.declaration.node.children:
        if n.name and n.span and (m:=p.match(n.name.strip())): out.append((m.group(1).strip(),n.span))
    return tuple(out)

def _errors(project,item):
    out=[]
    if item.declaration.kind=="error" and item.declaration.exported:
        vals={k:_clauses(item,k) for k in ("code","httpStatus","retry")}
        for key,v in vals.items():
            if len(v)!=1:
                x=_issue(item,"AIDL-T003",f"error '{item.declaration.name}' must declare exactly one {key}","stable code/status/retry contract",v[1][1] if len(v)>1 else None); out.extend([x] if x else [])
        if len(vals["code"])==1 and (not (m:=STRING.fullmatch(vals["code"][0][0])) or not m.group(1).strip()):
            x=_issue(item,"AIDL-T003","error code must be a non-empty string","stable string error code",vals["code"][0][1]); out.extend([x] if x else [])
        if len(vals["httpStatus"])==1:
            raw=vals["httpStatus"][0][0]
            if not re.fullmatch(r"\d{3}",raw) or not 400<=int(raw)<=599:
                x=_issue(item,"AIDL-T003",f"invalid public error httpStatus '{raw}'","4xx/5xx transport status",vals["httpStatus"][0][1]); out.extend([x] if x else [])
        if len(vals["retry"])==1 and not re.match(r"^(never|immediate|backoff|after)(?:\s|\(|$)",vals["retry"][0][0]):
            x=_issue(item,"AIDL-T003","invalid error retry class","never/immediate/backoff/after",vals["retry"][0][1]); out.extend([x] if x else [])
        msg=_clauses(item,"safeMessage")+_clauses(item,"localizationKey")
        if len(msg)!=1 or (len(msg)==1 and (not (m:=STRING.fullmatch(msg[0][0])) or not m.group(1).strip())):
            x=_issue(item,"AIDL-T003","error must declare exactly one non-empty safeMessage or localizationKey","safe public error message/localization",msg[1][1] if len(msg)>1 else (msg[0][1] if msg else None)); out.extend([x] if x else [])
    if item.declaration.kind in {"query","mutation"}:
        for raw,loc in _clauses(item,"errors"):
            if not(raw.startswith('[') and raw.endswith(']')):
                x=_issue(item,"AIDL-T003","errors clause must be a typed list","errors: [ErrorType, ...]",loc); out.extend([x] if x else []); continue
            try: names=_split(raw[1:-1]) if raw[1:-1].strip() else ()
            except TypeSyntaxError: names=("<malformed>",)
            seen=set()
            for name in names:
                clean=re.sub(r"\s*\.\s*",".",name); matches=_resolve(project,item,clean)
                valid=bool(NAME.fullmatch(clean)) and (clean.split('.')[-1] in STD_ERRORS or not matches or (len(matches)==1 and matches[0].declaration.kind=="error"))
                if not valid:
                    x=_issue(item,"AIDL-T003",f"declared error '{clean}' must resolve to an error declaration when it resolves in the current project","typed nominal errors; unresolved nominal rejection is M10-04",loc); out.extend([x] if x else [])
                if clean in seen:
                    x=_issue(item,"AIDL-T003",f"duplicate declared error '{clean}'","unique declared errors",loc); out.extend([x] if x else [])
                seen.add(clean)
    return out

def _api_ops(project,api):
    out=[]
    for raw,_ in _clauses(api,"operations"):
        if not(raw.startswith('[') and raw.endswith(']')): continue
        try: entries=_split(raw[1:-1])
        except TypeSyntaxError: continue
        for e in entries:
            if (m:=API_OP.fullmatch(e)):
                matches=[x for x in _resolve(project,api,re.sub(r"\s*\.\s*",".",m.group(2))) if x.declaration.kind==m.group(1)]
                if len(matches)==1: out.append(matches[0])
    return tuple(out)

def _serial(project,item,t,seen):
    if t.kind in {"scalar","entity-id"}: return True
    if t.kind=="ref": return False
    if t.kind in {"nullable","list","set"}: return _serial(project,item,t.args[0],seen)
    if t.kind=="map": return _map_key(project,item,t.args[0]) and _serial(project,item,t.args[1],seen)
    if t.kind!="named": return False
    if t.name in STD_TYPES or (t.name or '').split('.')[-1] in STD_TYPES: return all(_serial(project,item,a,seen) for a in t.args)
    matches=_resolve(project,item,t.name or '')
    if len(matches)!=1: return all(_serial(project,item,a,seen) for a in t.args)  # M10-04 owns unsupported names.
    target=matches[0]
    if target.declaration.kind not in {"alias","opaque","enum","value","entity","view"}: return False
    if _id(target) in seen: return True
    seen.add(_id(target))
    if target.declaration.kind in {"alias","opaque"}:
        raw=target.declaration.node.attrs.get("type")
        if isinstance(raw,str):
            try: return _serial(project,target,parse_type(raw),seen)
            except TypeSyntaxError: return False
    if target.declaration.kind=="value":
        for n in target.declaration.node.children:
            if (f:=_field(n)):
                if n.name and re.search(r"\bsensitive\b",n.name): return False
                try:
                    if not _serial(project,target,parse_type(f[1]),seen): return False
                except TypeSyntaxError: return False
    return all(_serial(project,item,a,seen) for a in t.args)

def _public(project,api):
    out=[]
    for op in _api_ops(project,api):
        sig=[]; raw=op.declaration.node.attrs.get("parameters")
        if isinstance(raw,str):
            try:
                for part in _params(raw):
                    if (m:=FIELD.match(part)): sig.append((f"parameter '{m.group(1)}'",_take(m.group(2))[0]))
            except TypeSyntaxError: pass
        ret=op.declaration.node.attrs.get("returns")
        if isinstance(ret,str) and ret.strip(): sig.append(("return",ret.strip()))
        for label,text in sig:
            try: ok=_serial(project,op,parse_type(text),set())
            except TypeSyntaxError: continue
            if not ok:
                x=_issue(op,"AIDL-T004",f"public API {label} type '{text}' is not serializable","public wire-safe Core type"); out.extend([x] if x else [])
    return out

def collect_type_issues(project:CompilerProject):
    out=[]; codes={}
    for item in project.declaration_names:
        d=item.declaration
        if d.kind in {"alias","opaque"}:
            raw=d.node.attrs.get("type")
            if isinstance(raw,str) and raw.strip(): out.extend(_check_type(project,item,raw.strip()))
        if d.kind in {"value","entity","error","event"}:
            for n in d.node.children:
                if (f:=_field(n)): out.extend(_check_type(project,item,f[1],n.span))
        if d.kind in {"query","mutation"}: out.extend(_signature(project,item)); out.extend(_errors(project,item))
        elif d.kind=="error": out.extend(_errors(project,item))
        if d.kind=="error" and d.exported:
            vals=_clauses(item,"code")
            if len(vals)==1 and (m:=STRING.fullmatch(vals[0][0])) and m.group(1):
                code=m.group(1)
                if code in codes:
                    x=_issue(item,"AIDL-T003",f"duplicate application error code '{code}'","application-unique error codes",vals[0][1]); out.extend([x] if x else [])
                else: codes[code]=item
    for api in project.declaration_names:
        if api.declaration.kind=="api": out.extend(_public(project,api))
    order={d.source_path:i for i,d in enumerate(project.documents)}
    out.sort(key=lambda x:(order.get(x.source_path,len(order)),x.location.offset,x.code,x.message))
    return tuple(out)
