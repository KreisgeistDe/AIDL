"""M16.5 E3 isolated schema-driven construction experiment; not production syntax."""
from __future__ import annotations

import argparse, hashlib, json, os, platform, re, statistics, subprocess, sys, time
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any

CANDIDATE_SCHEMA_ID = "urn:aidl:schema:language:m16.5-e3-candidate"
CANDIDATE_SCHEMA_VERSION = "m16.5-e3-candidate-v1"

class Cardinality(str, Enum):
    ONE="one"; OPTIONAL="optional"; MANY="many"
class ValueKind(str, Enum):
    IDENTIFIER="identifier"; STRING="string"; DURATION="duration"; IDENTIFIER_LIST="identifier-list"; TYPE="type"; RAW="raw"
@dataclass(frozen=True)
class ContextualTerminal: text: str
@dataclass(frozen=True)
class OrderedSlot: name: str; kind: ValueKind
@dataclass(frozen=True)
class KeyedChild:
    key: str; kind: ValueKind; cardinality: Cardinality=Cardinality.ONE
    contextual_terminal: ContextualTerminal|None=None; named: bool=False
@dataclass(frozen=True)
class WholeNodeAlternative: name: str; required_keys: tuple[str,...]=()
@dataclass(frozen=True)
class NodeShape:
    kind: str; ordered_slots: tuple[OrderedSlot,...]; keyed_children: tuple[KeyedChild,...]
    alternatives: tuple[WholeNodeAlternative,...]=(); construction_enabled: bool=True
    def child(self,key:str)->KeyedChild|None: return next((x for x in self.keyed_children if x.key==key),None)
    def validate(self)->None:
        keys=[x.key for x in self.keyed_children]
        if len(keys)!=len(set(keys)): raise ValueError(f"duplicate keyed child in {self.kind}")
        for alt in self.alternatives:
            if set(alt.required_keys)-set(keys): raise ValueError(f"bad alternative {alt.name}")
@dataclass(frozen=True)
class SchemaCatalog:
    schema_id: str; version: str; fingerprint: str; shapes: dict[str,NodeShape]
    def shape(self,kind:str)->NodeShape|None: return self.shapes.get(kind)
    def enabled_shapes(self): return (s for s in self.shapes.values() if s.construction_enabled)

def _shape(kind:str,*children:KeyedChild,alts:tuple[WholeNodeAlternative,...]=(),enabled:bool=True)->NodeShape:
    return NodeShape(kind,(OrderedSlot("name",ValueKind.IDENTIFIER),),children,alts,enabled)

@lru_cache(maxsize=1)
def build_catalog()->SchemaCatalog:
    f=ContextualTerminal("field"); M=Cardinality.MANY; O=Cardinality.OPTIONAL; I=ValueKind.IDENTIFIER
    shapes={
      "projection":_shape("projection",KeyedChild("source",I),KeyedChild("target",I)),
      "client":_shape("client",KeyedChild("service",I)),
      "migration":_shape("migration",KeyedChild("from",ValueKind.STRING),KeyedChild("to",ValueKind.STRING)),
      "consumer":_shape("consumer",KeyedChild("topic",I),KeyedChild("source",I)),
      "entity":_shape("entity",KeyedChild("field",ValueKind.TYPE,M,f,True)),
      "index":_shape("index",KeyedChild("fields",ValueKind.IDENTIFIER_LIST),KeyedChild("unique",ValueKind.RAW,O)),
      "queue_deadletter":_shape("queue_deadletter",KeyedChild("queue",I),KeyedChild("deadletter",I)),
      "schedule_lease":_shape("schedule_lease",KeyedChild("schedule",I),KeyedChild("lease",ValueKind.DURATION)),
      "sync_outbox":_shape("sync_outbox",KeyedChild("changes",I),KeyedChild("outbox",I)),
      "app":_shape("app",KeyedChild("version",ValueKind.STRING),KeyedChild("module",I,O)),
      "service":_shape("service",KeyedChild("api",I,O),KeyedChild("resource",I,M)),
      "api":_shape("api",KeyedChild("route",ValueKind.RAW,M)),
      "event":_shape("event",KeyedChild("field",ValueKind.TYPE,M,f,True)),
      "workflow":_shape("workflow",KeyedChild("step",ValueKind.RAW,M),alts=(WholeNodeAlternative("ordered-steps",("step",)),)),
      "deployment":_shape("deployment",KeyedChild("target",I),KeyedChild("resource",ValueKind.RAW,M)),
      "uiStatement":_shape("uiStatement",enabled=False), "testStatement":_shape("testStatement",enabled=False),
    }
    for shape in shapes.values(): shape.validate()
    raw=json.dumps({k:repr(v) for k,v in sorted(shapes.items())},sort_keys=True).encode()
    return SchemaCatalog(CANDIDATE_SCHEMA_ID,CANDIDATE_SCHEMA_VERSION,"sha256:"+hashlib.sha256(raw).hexdigest(),shapes)

TOKEN_RE=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z0-9_.]*|-?\d+(?:\.\d+)?(?:ms|s|m|h|d)?|\[|\]|\{|\}|:|,|\S',re.S)
HEADER_RE=re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*(?://[^\n]*)?$')
CHILD_RE=re.compile(r'^\s*(\w+)\s+(\w+)\s*:\s*(.*?)\s*$'); KEY_RE=re.compile(r'^\s*(\w+)\s*:\s*(.*?)\s*$')
IDENT_RE=re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*$'); DURATION_RE=re.compile(r'^\d+(?:\.\d+)?(?:ms|s|m|h|d)$')
LEGACY_RE=re.compile(r'\b(from\s+\[|\sinto\b|\sfor\s+[A-Z]|\son\s+\w+\s+from\s+|deadLetter\s+\(|changes\s+\w+\s+via\s+outbox)')
@dataclass(frozen=True)
class Diagnostic: code:str; message:str; offset:int=0
class ConstructionError(ValueError):
    def __init__(self,d:Diagnostic): super().__init__(f"{d.code}: {d.message}"); self.diagnostic=d
@dataclass(frozen=True)
class ConcreteToken: lexeme:str; start:int; end:int; trivia:bool
@dataclass(frozen=True)
class SourceAnchor: role:str; start:int; end:int
@dataclass(frozen=True)
class LosslessSidecar:
    source:str; source_fingerprint:str; schema_fingerprint:str; tokens:tuple[ConcreteToken,...]; anchors:tuple[SourceAnchor,...]
@dataclass(frozen=True)
class SemanticNode: kind:str; name:str; values:dict[str,Any]
@dataclass(frozen=True)
class ConstructionResult: node:SemanticNode; sidecar:LosslessSidecar

def _fail(code:str,msg:str,offset:int=0)->None: raise ConstructionError(Diagnostic(code,msg,offset))
def _tokens(source:str)->tuple[ConcreteToken,...]:
    out=[]; cursor=0
    for m in TOKEN_RE.finditer(source):
        if m.start()>cursor: out.append(ConcreteToken(source[cursor:m.start()],cursor,m.start(),True))
        x=m.group(); out.append(ConcreteToken(x,m.start(),m.end(),x.startswith("//") or x.startswith("/*"))); cursor=m.end()
    if cursor<len(source): out.append(ConcreteToken(source[cursor:],cursor,len(source),True))
    return tuple(out)
def _strip_comment(text:str)->str:
    quoted=False; escaped=False
    for i,ch in enumerate(text[:-1]):
        if quoted and escaped: escaped=False; continue
        if quoted and ch=="\\": escaped=True; continue
        if ch=='"': quoted=not quoted
        if not quoted and text[i:i+2]=="//": return text[:i].rstrip()
    return text.rstrip()
def _value(raw:str,child:KeyedChild)->Any:
    raw=raw.strip()
    if child.kind in (ValueKind.IDENTIFIER,ValueKind.TYPE):
        if not IDENT_RE.fullmatch(raw): _fail("AIDL-S004",f"{child.key} requires identifier/type")
        return raw
    if child.kind is ValueKind.STRING:
        if len(raw)<2 or raw[0]!='"' or raw[-1]!='"': _fail("AIDL-S004",f"{child.key} requires quoted string")
        return raw[1:-1]
    if child.kind is ValueKind.DURATION:
        if not DURATION_RE.fullmatch(raw): _fail("AIDL-S004",f"{child.key} requires duration")
        return raw
    if child.kind is ValueKind.IDENTIFIER_LIST:
        if not(raw.startswith("[") and raw.endswith("]")): _fail("AIDL-S004",f"{child.key} requires identifier list")
        xs=[x.strip() for x in raw[1:-1].split(",") if x.strip()]
        if not xs or any(not IDENT_RE.fullmatch(x) for x in xs): _fail("AIDL-S004",f"{child.key} requires identifier list")
        return xs
    return raw

def parse_candidate(source:str,*,source_version:str,schema_version:str|None=None)->ConstructionResult:
    cat=build_catalog(); schema_version=schema_version or source_version
    if source_version!=cat.version or schema_version!=cat.version: _fail("AIDL-S008","explicit source/schema version mismatch")
    if LEGACY_RE.search(source): _fail("AIDL-S007","legacy spelling rejected; no fallback/sniffing")
    lines=source.splitlines(keepends=True); meaningful=[(i,l) for i,l in enumerate(lines) if l.strip() and not l.lstrip().startswith("//")]
    if len(meaningful)<2: _fail("AIDL-S001","declaration header/body required")
    hi,hl=meaningful[0]; hm=HEADER_RE.match(hl.rstrip("\r\n"))
    if not hm: _fail("AIDL-S005","expected '<kind> <name> {'")
    kind,name=hm.groups(); shape=cat.shape(kind)
    if shape is None: _fail("AIDL-S003",f"unknown construction kind {kind}")
    if not shape.construction_enabled: _fail("AIDL-S005",f"{kind} intentionally outside E3 construction")
    ci,cl=meaningful[-1]
    if cl.strip()!="}": _fail("AIDL-S005","declaration must end with '}'")
    offsets=[]; n=0
    for line in lines: offsets.append(n); n+=len(line)
    anchors=[SourceAnchor("declaration-header",offsets[hi],offsets[hi]+len(hl.rstrip("\r\n")))]; values={}; counts={}
    for i,line in meaningful[1:-1]:
        text=_strip_comment(line.rstrip("\r\n")); cm=CHILD_RE.match(text); child_name=None
        if cm and (candidate:=shape.child(cm.group(1))) is not None and candidate.named: key,child_name,raw=cm.groups()
        else:
            km=KEY_RE.match(text)
            if not km: _fail("AIDL-S005",f"malformed body item line {i+1}",offsets[i])
            key,raw=km.groups()
        child=shape.child(key)
        if child is None: _fail("AIDL-S003",f"unknown structural item {key}",offsets[i])
        if child.named and child_name is None: _fail("AIDL-S005",f"{key} requires named child",offsets[i])
        counts[key]=counts.get(key,0)+1
        if child.cardinality is not Cardinality.MANY and counts[key]>1: _fail("AIDL-S002",f"duplicate {key}",offsets[i])
        parsed=_value(raw,child); parsed={"name":child_name,"value":parsed} if child.named else parsed
        if child.cardinality is Cardinality.MANY: values.setdefault(key,[]).append(parsed)
        else: values[key]=parsed
        anchors.append(SourceAnchor(f"body:{key}",offsets[i],offsets[i]+len(line.rstrip("\r\n"))))
    for child in shape.keyed_children:
        if child.cardinality is Cardinality.ONE and counts.get(child.key,0)!=1: _fail("AIDL-S001",f"missing {child.key}")
    if shape.alternatives and not any(all(k in values for k in a.required_keys) for a in shape.alternatives): _fail("AIDL-S004",f"no alternative for {kind}")
    anchors.append(SourceAnchor("declaration",offsets[hi],offsets[ci]+len(cl.rstrip("\r\n"))))
    side=LosslessSidecar(source,"sha256:"+hashlib.sha256(source.encode()).hexdigest(),cat.fingerprint,_tokens(source),tuple(anchors))
    return ConstructionResult(SemanticNode(kind,name,values),side)

WORKLOAD="projection BenchProjection {\n  source: OrderCreated\n  target: CustomerView\n}\n"
def _one()->int:
    start=time.perf_counter_ns(); cat=build_catalog(); parse_candidate(WORKLOAD,source_version=cat.version,schema_version=cat.version); return time.perf_counter_ns()-start
def _summary(xs:list[int])->dict[str,float|int]:
    return {"min_ns":min(xs),"median_ns":statistics.median(xs),"mean_ns":statistics.fmean(xs),"max_ns":max(xs),"pstdev_ns":statistics.pstdev(xs)}
def run_benchmark()->dict[str,Any]:
    cold=[int(subprocess.run([sys.executable,"-m","tools.m16_5_e3_prototype","--single"],check=True,capture_output=True,text=True).stdout) for _ in range(10)]
    for _ in range(5): _one()
    warm=[_one() for _ in range(30)]
    return {"protocol":{"cold_fresh_process_runs":10,"warmups_same_process":5,"warm_measured_same_process":30,"threshold":None},"machine":{"platform":platform.platform(),"python":sys.version.split()[0],"architecture":platform.machine(),"cpu_count":os.cpu_count()},"cold_ns":cold,"warm_ns":warm,"cold_summary":_summary(cold),"warm_summary":_summary(warm),"catalog_cache":build_catalog.cache_info()._asdict(),"schema_filesystem_loads":0}
def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--benchmark",action="store_true"); p.add_argument("--single",action="store_true"); a=p.parse_args()
    if a.single: print(_one())
    elif a.benchmark: print(json.dumps(run_benchmark(),indent=2,sort_keys=True))
    else: p.error("choose --benchmark or --single")
if __name__=="__main__": main()
