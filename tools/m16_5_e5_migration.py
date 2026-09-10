"""M16.5 E5 isolated old-to-candidate migration/formatting experiment."""
from __future__ import annotations
import hashlib,json,re
from dataclasses import dataclass,replace
from typing import Any,Iterable
from tools.aidl_parser import parse_text
from tools.m16_5_e3_prototype import CANDIDATE_SCHEMA_VERSION as E3_VERSION, parse_candidate as parse_e3_candidate
OLD_SCHEMA_ID="urn:aidl:schema:language:m16.5-e5-current"; OLD_VERSION="m16.5-e5-current-v1"
TARGET_SCHEMA_ID="urn:aidl:schema:language:m16.5-e5-candidate"; TARGET_VERSION="m16.5-e5-candidate-v2"
ROW_IDS=("projection-relationship","client-target","migration-source-target","consumer-relationship","explicit-field-child","explicit-index","queue-deadletter","schedule-lease","sync-outbox")
_SCHEMA_PAYLOAD={"old":{"id":OLD_SCHEMA_ID,"version":OLD_VERSION,"rows":ROW_IDS},"target":{"id":TARGET_SCHEMA_ID,"version":TARGET_VERSION,"rows":ROW_IDS}}
def _fp(x): return "sha256:"+hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
OLD_SCHEMA_FINGERPRINT=_fp(_SCHEMA_PAYLOAD["old"]); TARGET_SCHEMA_FINGERPRINT=_fp(_SCHEMA_PAYLOAD["target"])
FACT_COMPLETE_ROW_IDS=ROW_IDS
@dataclass(frozen=True)
class Diagnostic: code:str; message:str; offset:int=0
class MigrationError(ValueError):
 def __init__(self,d): super().__init__(f"{d.code}: {d.message}"); self.diagnostic=d
@dataclass(frozen=True)
class Anchor: anchor_id:str; row_id:str; role:str; start:int; end:int
@dataclass(frozen=True)
class LosslessSidecar: source:str; source_fingerprint:str; source_version:str; schema_fingerprint:str; anchors:tuple[Anchor,...]
@dataclass(frozen=True)
class Edit: anchor_id:str; row_id:str; start:int; end:int; replacement:str
@dataclass(frozen=True)
class Relocation: anchor_id:str; old_start:int; old_end:int; new_start:int; new_end:int
@dataclass(frozen=True)
class SemanticFact: row_id:str; identity:str; facts:tuple[tuple[str,Any],...]
@dataclass(frozen=True)
class MigrationPlan:
 source_version:str; old_version:str; target_version:str; old_schema_fingerprint:str; target_schema_fingerprint:str; source_fingerprint:str; edits:tuple[Edit,...]; relocations:tuple[Relocation,...]; semantic_result:str; old_facts:tuple[SemanticFact,...]; target_facts:tuple[SemanticFact,...]; rollback_source:str; e3_replayed_rows:tuple[str,...]; diagnostics:tuple[Diagnostic,...]=()
@dataclass(frozen=True)
class MigrationResult: source:str; plan:MigrationPlan
@dataclass(frozen=True)
class _Rule: row_id:str; role:str; old_re:re.Pattern[str]; candidate_re:re.Pattern[str]
def _rx(p,flags=re.MULTILINE):return re.compile(p,flags)
RULES=(
 _Rule("projection-relationship","declaration-header",_rx(r"^(?P<i>[ \t]*)projection[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+from[ \t]+\[(?P<sources>[^\]\n]+)\][ \t]+into[ \t]+(?P<target>[A-Za-z_][\w.]*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]*)projection[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P<source_lines>(?:(?P=i)  source:[ \t]*[A-Za-z_][\w.]*\n)+)(?P=i)  target:[ \t]*(?P<target>[A-Za-z_][\w.]*)$")),
 _Rule("client-target","declaration-header",_rx(r"^(?P<i>[ \t]*)client[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+for[ \t]+(?P<service>[A-Za-z_][\w.]*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]*)client[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P=i)  service:[ \t]*(?P<service>[A-Za-z_][\w.]*)$")),
 _Rule("migration-source-target","declaration-header",_rx(r'^(?P<i>[ \t]*)migration[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+from[ \t]+(?P<from>"(?:\\.|[^"\\])*")[ \t]+to[ \t]+(?P<to>"(?:\\.|[^"\\])*")[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$'),_rx(r'^(?P<i>[ \t]*)migration[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P=i)  from:[ \t]*(?P<from>"(?:\\.|[^"\\])*")\n(?P=i)  to:[ \t]*(?P<to>"(?:\\.|[^"\\])*")$')),
 _Rule("consumer-relationship","declaration-header",_rx(r"^(?P<i>[ \t]*)consumer[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+on[ \t]+(?P<topic>[A-Za-z_][\w.]*)[ \t]+from[ \t]+(?P<source>[A-Za-z_][\w.]*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]*)consumer[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P=i)  topic:[ \t]*(?P<topic>[A-Za-z_][\w.]*)\n(?P=i)  source:[ \t]*(?P<source>[A-Za-z_][\w.]*)$")),
 _Rule("explicit-field-child","body-entry",_rx(r"^(?P<i>[ \t]+)(?!field\b)(?P<name>[A-Za-z_]\w*)[ \t]*:[ \t]*(?P<type>[A-Za-z_][\w.<>\[\]?]*)?(?P<mods>(?:[ \t]+[^/\n]+?)?)(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]+)field[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*:[ \t]*(?P<type>[A-Za-z_][\w.<>\[\]?]*)(?P<mods>(?:[ \t]+[^/\n]+?)?)(?P<tail>[ \t]*(?://[^\n]*)?)$")),
 _Rule("explicit-index","body-entry",_rx(r"^(?P<i>[ \t]+)index[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\((?P<fields>[^)\n]+)\)(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]+)index[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*:[ \t]*\((?P<fields>[^)\n]+)\)(?P<tail>[ \t]*(?://[^\n]*)?)$")),
 _Rule("queue-deadletter","body-entry",_rx(r"^(?P<i>[ \t]+)deadLetter[ \t]+after[ \t]+(?P<count>\d+)[ \t]+attempts(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]+)deadLetter[ \t]*:[ \t]*(?P<count>\d+)[ \t]+attempts(?P<tail>[ \t]*(?://[^\n]*)?)$")),
 _Rule("schedule-lease","body-entry",_rx(r"^(?P<i>[ \t]+)singleton[ \t]+lease[ \t]+(?P<duration>\d+(?:\.\d+)?(?:ms|s|m|h|d))(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]+)singleton[ \t]*:[ \t]*lease[ \t]+(?P<duration>\d+(?:\.\d+)?(?:ms|s|m|h|d))(?P<tail>[ \t]*(?://[^\n]*)?)$")),
 _Rule("sync-outbox","body-entry",_rx(r"^(?P<i>[ \t]+)changes[ \t]+to[ \t]+(?P<target>[A-Za-z_][\w.]*)[ \t]+via[ \t]+outbox(?P<tail>[ \t]*(?://[^\n]*)?)$"),_rx(r"^(?P<i>[ \t]+)changes[ \t]*:[ \t]*(?P<target>[A-Za-z_][\w.]*)[ \t]+via[ \t]+outbox(?P<tail>[ \t]*(?://[^\n]*)?)$")),
)
SCHEDULE_HEADER_RE=_rx(r"^[ \t]*schedule[ \t]+[A-Za-z_]\w*[ \t]*\{[ \t]*(?://[^\n]*)?$"); SCHEDULE_CLOSE_RE=_rx(r"^[ \t]*}[ \t]*(?://[^\n]*)?$")
def source_fingerprint(source):return "sha256:"+hashlib.sha256(source.encode()).hexdigest()
def _fail(c,m,o=0):raise MigrationError(Diagnostic(c,m,o))
def _matches(source,*,candidate):
 for rule in RULES:
  p=rule.candidate_re if candidate else rule.old_re
  for m in p.finditer(source):
   if rule.row_id=="explicit-field-child":
    prefix=source[:m.start()]; opener=prefix.rfind("entity "); close=prefix.rfind("}")
    if opener<0 or opener<close:continue
   yield rule,m
def build_sidecar(source,*,source_version,schema_fingerprint):
 if source_version==OLD_VERSION:candidate=False; expected=OLD_SCHEMA_FINGERPRINT
 elif source_version==TARGET_VERSION:candidate=True; expected=TARGET_SCHEMA_FINGERPRINT
 else:_fail("AIDL-S008",f"unknown source version {source_version!r}")
 if schema_fingerprint!=expected:_fail("AIDL-S008","source/schema fingerprint mismatch")
 counts={}; anchors=[]
 for r,m in _matches(source,candidate=candidate):
  i=counts.get(r.row_id,0);counts[r.row_id]=i+1;anchors.append(Anchor(f"{r.row_id}:{i}",r.row_id,r.role,m.start(),m.end()))
 return LosslessSidecar(source,source_fingerprint(source),source_version,schema_fingerprint,tuple(anchors))
def _clean_csv(v):return tuple(x.strip() for x in v.split(",") if x.strip())
def _index_fields(v):
 out=[]
 for raw in _clean_csv(v):
  bits=raw.split()
  if len(bits)==1:out.append((bits[0],"default"))
  elif len(bits)==2 and bits[1] in {"asc","desc"}:out.append((bits[0],bits[1]))
  else:_fail("AIDL-S004",f"unsupported bounded index field {raw!r}")
 return tuple(out)
def _candidate_sources(m): return tuple(re.findall(r"(?m)^\s*source:\s*([A-Za-z_][\w.]*)\s*$",m.group("source_lines")))
def _enclosing(source,offset,kinds):
 ms=list(re.compile(r"(?m)^(?P<i>[ \t]*)(?P<kind>"+"|".join(map(re.escape,kinds))+r")[ \t]+(?P<name>[A-Za-z_]\w*)\b[^{\n]*\{").finditer(source[:offset]))
 if not ms:_fail("AIDL-S005",f"cannot resolve enclosing {'/'.join(kinds)} declaration",offset)
 return ms[-1]
def _fact(r,m,source,*,candidate):
 g=m.groupdict(); row=r.row_id
 if row=="projection-relationship": identity=g["name"]; facts=(("sources",_candidate_sources(m) if candidate else _clean_csv(g["sources"])),("target",g["target"]))
 elif row=="client-target":identity=g["name"];facts=(("service",g["service"]),)
 elif row=="migration-source-target":identity=g["name"];facts=(("from",g["from"][1:-1]),("to",g["to"][1:-1]))
 elif row=="consumer-relationship":identity=g["name"];facts=(("topic",g["topic"]),("source",g["source"]))
 elif row=="explicit-field-child":identity=g["name"];facts=(("type",g["type"]),("modifiers",tuple((g.get("mods") or "").strip().split())))
 elif row=="explicit-index":identity=g["name"];facts=(("fields",_index_fields(g["fields"])),)
 elif row=="queue-deadletter":e=_enclosing(source,m.start(),("queue","topic"));identity=e.group("name");facts=(("attempts",int(g["count"])),("owner_kind",e.group("kind")))
 elif row=="schedule-lease":identity=_enclosing(source,m.start(),("schedule",)).group("name");facts=(("mode","singleton"),("lease",g["duration"]))
 elif row=="sync-outbox":identity=_enclosing(source,m.start(),("sync",)).group("name");facts=(("target",g["target"]),("delivery","outbox"))
 else:raise AssertionError(row)
 return SemanticFact(row,identity,tuple(facts))
def extract_facts(source,*,source_version):
 if source_version==OLD_VERSION:c=False
 elif source_version==TARGET_VERSION:c=True
 else:_fail("AIDL-S008",f"unknown source version {source_version!r}")
 return tuple(sorted((_fact(r,m,source,candidate=c) for r,m in _matches(source,candidate=c)),key=lambda f:(ROW_IDS.index(f.row_id),f.identity)))
def _replacement(r,m):
 g=m.groupdict();i=g.get("i") or "";tail=g.get("tail") or "";row=r.row_id
 if row=="projection-relationship":
  srcs=_clean_csv(g["sources"]); lines="\n".join(f"{i}  source: {s}" for s in srcs); return f"{i}projection {g['name']} {{{tail}\n{lines}\n{i}  target: {g['target']}"
 if row=="client-target":return f"{i}client {g['name']} {{{tail}\n{i}  service: {g['service']}"
 if row=="migration-source-target":return f"{i}migration {g['name']} {{{tail}\n{i}  from: {g['from']}\n{i}  to: {g['to']}"
 if row=="consumer-relationship":return f"{i}consumer {g['name']} {{{tail}\n{i}  topic: {g['topic']}\n{i}  source: {g['source']}"
 if row=="explicit-field-child":mods=" "+" ".join((g.get("mods") or "").strip().split()) if (g.get("mods") or "").strip() else "";return f"{i}field {g['name']}: {g['type']}{mods}{tail}"
 if row=="explicit-index":fields=", ".join(" ".join(x) if x[1]!="default" else x[0] for x in _index_fields(g["fields"]));return f"{i}index {g['name']}: ({fields}){tail}"
 if row=="queue-deadletter":return f"{i}deadLetter: {g['count']} attempts{tail}"
 if row=="schedule-lease":return f"{i}singleton: lease {g['duration']}{tail}"
 if row=="sync-outbox":return f"{i}changes: {g['target']} via outbox{tail}"
 raise AssertionError(row)
def _known_schedule_parser_gap(source,diagnostics,row_ids):
 if set(row_ids)!={"schedule-lease"} or not diagnostics or any(x.message!="expected declaration" for x in diagnostics):return False
 h=SCHEDULE_HEADER_RE.search(source);c=SCHEDULE_CLOSE_RE.search(source);ls=[m for r,m in _matches(source,candidate=False) if r.row_id=="schedule-lease"]
 return bool(h and c and len(ls)==1 and h.end()<=ls[0].start() and ls[0].end()<=c.start())
def _validate_old_source(source):
 rows=tuple(r.row_id for r,_ in _matches(source,candidate=False));_,ds,_=parse_text(source)
 if not ds or _known_schedule_parser_gap(source,ds,rows):return
 first=ds[0];_fail("AIDL-S005",f"legacy fixture is not accepted by production parser: {first.message}",getattr(getattr(first,'start',None),'offset',0))
def _validate_sidecar(s,source,expected):
 if s.source!=source or s.source_fingerprint!=source_fingerprint(source):_fail("AIDL-S008","stale source fingerprint")
 if s.schema_fingerprint!=expected:_fail("AIDL-S008","stale schema fingerprint")
 prev=-1;seen=set()
 for a in sorted(s.anchors,key=lambda x:(x.start,x.end,x.anchor_id)):
  if a.anchor_id in seen:_fail("AIDL-S005",f"ambiguous anchor {a.anchor_id}",a.start)
  if a.start<prev:_fail("AIDL-S005",f"overlapping anchor {a.anchor_id}",a.start)
  seen.add(a.anchor_id);prev=max(prev,a.end)
def _apply(source,edits):
 cursor=0;out=[];rels=[];new=0
 for e in sorted(edits,key=lambda x:(x.start,x.end)):
  if e.start<cursor:_fail("AIDL-S005",f"overlapping edit {e.anchor_id}",e.start)
  u=source[cursor:e.start];out.append(u);new+=len(u);ns=new;out.append(e.replacement);new+=len(e.replacement);rels.append(Relocation(e.anchor_id,e.start,e.end,ns,new));cursor=e.end
 out.append(source[cursor:]);return "".join(out),tuple(rels)
def _candidate_is_valid(source):
 lingering=list(_matches(source,candidate=False))
 if lingering:_fail("AIDL-S007",f"legacy spelling remains for {lingering[0][0].row_id}",lingering[0][1].start())
 extract_facts(source,source_version=TARGET_VERSION)
def _e3_replay(facts):
 replay=[]
 for f in facts:
  v=dict(f.facts)
  if f.row_id=="projection-relationship": snippet=f"projection {f.identity} {{\n"+"".join(f"  source: {x}\n" for x in v['sources'])+f"  target: {v['target']}\n}}\n"
  elif f.row_id=="client-target":snippet=f"client {f.identity} {{\n  service: {v['service']}\n}}\n"
  elif f.row_id=="migration-source-target":snippet=f"migration {f.identity} {{\n  from: \"{v['from']}\"\n  to: \"{v['to']}\"\n}}\n"
  elif f.row_id=="consumer-relationship":snippet=f"consumer {f.identity} {{\n  topic: {v['topic']}\n  source: {v['source']}\n}}\n"
  elif f.row_id=="explicit-field-child":snippet=f"entity E5Replay {{\n  field {f.identity}: {v['type']}\n}}\n"
  elif f.row_id=="explicit-index":snippet=f"index {f.identity} {{\n  fields: ["+", ".join(x[0]+(" "+x[1] if x[1]!="default" else "") for x in v['fields'])+"]\n}\n"
  elif f.row_id=="queue-deadletter":snippet=f"queue_deadletter {f.identity} {{\n  queue: {f.identity}\n  attempts: {v['attempts']}\n}}\n"
  elif f.row_id=="schedule-lease":snippet=f"schedule_lease {f.identity} {{\n  schedule: {f.identity}\n  singleton: true\n  lease: {v['lease']}\n}}\n"
  elif f.row_id=="sync-outbox":snippet=f"sync_outbox {f.identity} {{\n  changes: {v['target']}\n  delivery: outbox\n}}\n"
  else:continue
  parse_e3_candidate(snippet,source_version=E3_VERSION,schema_version=E3_VERSION);replay.append(f.row_id)
 return tuple(replay)
def format_candidate(source,*,source_version,schema_fingerprint):
 if source_version!=TARGET_VERSION or schema_fingerprint!=TARGET_SCHEMA_FINGERPRINT:_fail("AIDL-S008","Formatter(v) requires exact selected candidate schema")
 if list(_matches(source,candidate=False)):_fail("AIDL-S007","Formatter(target) does not accept legacy spelling")
 # canonicalize only non-projection candidate anchors; projection source order/multiplicity is preserved.
 edits=[];side=build_sidecar(source,source_version=TARGET_VERSION,schema_fingerprint=schema_fingerprint);by={a.anchor_id:a for a in side.anchors};counts={}
 for r,m in _matches(source,candidate=True):
  idx=counts.get(r.row_id,0);counts[r.row_id]=idx+1;aid=f"{r.row_id}:{idx}";g=m.groupdict();i=g.get("i") or "";tail=g.get("tail") or ""
  if r.row_id=="projection-relationship": rep=m.group(0)
  elif r.row_id=="client-target":rep=f"{i}client {g['name']} {{{tail}\n{i}  service: {g['service']}"
  elif r.row_id=="migration-source-target":rep=f"{i}migration {g['name']} {{{tail}\n{i}  from: {g['from']}\n{i}  to: {g['to']}"
  elif r.row_id=="consumer-relationship":rep=f"{i}consumer {g['name']} {{{tail}\n{i}  topic: {g['topic']}\n{i}  source: {g['source']}"
  elif r.row_id=="explicit-field-child":mods=" "+" ".join((g.get("mods") or "").strip().split()) if (g.get("mods") or "").strip() else "";rep=f"{i}field {g['name']}: {g['type']}{mods}{tail}"
  elif r.row_id=="explicit-index":fields=", ".join(" ".join(x) if x[1]!="default" else x[0] for x in _index_fields(g["fields"]));rep=f"{i}index {g['name']}: ({fields}){tail}"
  elif r.row_id=="queue-deadletter":rep=f"{i}deadLetter: {g['count']} attempts{tail}"
  elif r.row_id=="schedule-lease":rep=f"{i}singleton: lease {g['duration']}{tail}"
  elif r.row_id=="sync-outbox":rep=f"{i}changes: {g['target']} via outbox{tail}"
  else:raise AssertionError(r.row_id)
  if rep!=m.group(0): edits.append(Edit(aid,r.row_id,m.start(),m.end(),rep))
 return _apply(source,tuple(edits))[0]
def plan_migration(source,*,source_version,old_version,target_version,source_schema_fingerprint,target_schema_fingerprint,expected_source_fingerprint,sidecar=None):
 if old_version!=OLD_VERSION or target_version!=TARGET_VERSION:_fail("AIDL-S008","unknown or stale migration version pair")
 if target_schema_fingerprint!=TARGET_SCHEMA_FINGERPRINT:_fail("AIDL-S008","unknown or stale target schema fingerprint")
 if expected_source_fingerprint!=source_fingerprint(source):_fail("AIDL-S008","stale source fingerprint")
 if source_version==TARGET_VERSION:
  if source_schema_fingerprint!=TARGET_SCHEMA_FINGERPRINT:_fail("AIDL-S008","target source/schema fingerprint mismatch")
  sidecar=sidecar or build_sidecar(source,source_version=TARGET_VERSION,schema_fingerprint=source_schema_fingerprint);_validate_sidecar(sidecar,source,TARGET_SCHEMA_FINGERPRINT);_candidate_is_valid(source);facts=extract_facts(source,source_version=TARGET_VERSION);return MigrationPlan(source_version,old_version,target_version,OLD_SCHEMA_FINGERPRINT,TARGET_SCHEMA_FINGERPRINT,source_fingerprint(source),(),(),"compatible",facts,facts,source,_e3_replay(facts))
 if source_version!=OLD_VERSION or source_schema_fingerprint!=OLD_SCHEMA_FINGERPRINT:_fail("AIDL-S008","old source/schema fingerprint mismatch")
 _validate_old_source(source);sidecar=sidecar or build_sidecar(source,source_version=OLD_VERSION,schema_fingerprint=source_schema_fingerprint);_validate_sidecar(sidecar,source,OLD_SCHEMA_FINGERPRINT);anchors={a.anchor_id:a for a in sidecar.anchors};counts={};edits=[]
 for r,m in _matches(source,candidate=False):
  idx=counts.get(r.row_id,0);counts[r.row_id]=idx+1;aid=f"{r.row_id}:{idx}";a=anchors.get(aid)
  if a is None or (a.start,a.end)!=(m.start(),m.end()):_fail("AIDL-S005",f"missing or stale anchor {aid}",m.start())
  edits.append(Edit(aid,r.row_id,m.start(),m.end(),_replacement(r,m)))
 migrated,rels=_apply(source,tuple(edits));formatted=format_candidate(migrated,source_version=TARGET_VERSION,schema_fingerprint=TARGET_SCHEMA_FINGERPRINT);_candidate_is_valid(formatted);old=extract_facts(source,source_version=OLD_VERSION);target=extract_facts(formatted,source_version=TARGET_VERSION)
 if old!=target:_fail("AIDL-S004","bounded semantic fact comparison is not compatible")
 if formatted!=migrated:_fail("AIDL-S005","migrator emitted non-canonical target source")
 replay=_e3_replay(target)
 if set(f.row_id for f in target)-set(replay):_fail("AIDL-S004","E3 v2 replay did not prove all modeled target rows")
 return MigrationPlan(source_version,old_version,target_version,OLD_SCHEMA_FINGERPRINT,TARGET_SCHEMA_FINGERPRINT,source_fingerprint(source),tuple(edits),rels,"compatible",old,target,source,replay)
def apply_plan(source,plan):
 if plan.source_fingerprint!=source_fingerprint(source):_fail("AIDL-S008","stale source fingerprint at apply")
 migrated,rels=_apply(source,plan.edits)
 if rels!=plan.relocations:_fail("AIDL-S005","non-deterministic relocation metadata")
 if extract_facts(migrated,source_version=TARGET_VERSION)!=plan.target_facts:_fail("AIDL-S004","semantic facts changed while applying plan")
 return MigrationResult(migrated,plan)
def migrate(source,**kwargs):
 p=plan_migration(source,**kwargs);return apply_plan(source,p) if p.edits else MigrationResult(source,p)
def with_anchors(sidecar,anchors:Iterable[Anchor]):return replace(sidecar,anchors=tuple(anchors))
