"""M16.5 evaluation-only candidate-work-product -> current compiler projection.

Experimental prerequisite only: no production parser/IR authority and no E8 runner.
"""
from __future__ import annotations

import copy, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from re import _constants as C, _parser as RP
from typing import Any, Mapping

from tools import m16_5_e3_prototype as e3
from tools import m16_5_e4_introspection as e4
from tools import m16_5_e5_migration as e5

ROOT=Path(__file__).resolve().parents[1]
PROJECTION_ID="urn:aidl:evaluation:m16.5-candidate-current-projection"
PROJECTION_VERSION="1"

class ProjectionError(RuntimeError):
 def __init__(self,reason,detail,*,evidence=None):
  super().__init__(f"{reason}: {detail}");self.reason=reason;self.detail=detail;self.evidence=evidence

@dataclass(frozen=True)
class ProjectionRef: projection_id:str;semantic_version:str;content_fingerprint:str
@dataclass(frozen=True)
class ProjectionContext:
 projection_ref:ProjectionRef;e3_schema_id:str;e3_schema_version:str;e3_schema_fingerprint:str;e4_schema_id:str;e4_schema_version:str;e4_schema_fingerprint:str;candidate_schema_id:str;candidate_schema_version:str;candidate_schema_fingerprint:str;current_schema_id:str;current_schema_version:str;current_schema_fingerprint:str
@dataclass(frozen=True)
class SourceProjection:
 candidate_fingerprint:str;current_fingerprint:str;row_ids:tuple[str,...];candidate_facts:tuple[e5.SemanticFact,...];current_facts:tuple[e5.SemanticFact,...];source:str
@dataclass(frozen=True)
class CompilerCommandEvidence:
 command:str;argv:tuple[str,...];exit_code:int;ok:bool;diagnostics:tuple[dict[str,Any],...];result:Any|None;stdout_sha256:str;stderr:str
@dataclass(frozen=True)
class CompilerEvidence:
 check:CompilerCommandEvidence;ir:CompilerCommandEvidence
 @property
 def accepted(self):return self.check.ok and self.ir.ok and self.check.exit_code==0 and self.ir.exit_code==0
@dataclass(frozen=True)
class ProjectProjection:
 projection_ref:ProjectionRef;output_root:str;files:tuple[tuple[str,SourceProjection],...];compiler:CompilerEvidence

def _sha(s):return "sha256:"+hashlib.sha256(s.encode()).hexdigest()
def _j(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def _payload():
 a=e3.build_catalog();b=e4.current_schema_ref()
 return {"projection_id":PROJECTION_ID,"semantic_version":PROJECTION_VERSION,"authority":{"e3":{"schema_id":a.schema_id,"semantic_version":a.version,"content_fingerprint":a.fingerprint},"e4":asdict(b),"e5_current":{"schema_id":e5.OLD_SCHEMA_ID,"semantic_version":e5.OLD_VERSION,"content_fingerprint":e5.OLD_SCHEMA_FINGERPRINT},"e5_candidate":{"schema_id":e5.TARGET_SCHEMA_ID,"semantic_version":e5.TARGET_VERSION,"content_fingerprint":e5.TARGET_SCHEMA_FINGERPRINT},"normalization_rows":list(e5.ROW_IDS)},"output":{"source_language":"accepted/current","compiler_authority":["aidl check","aidl ir"]},"inverse_rule_source":"tools.m16_5_e5_migration.RULES","semantics":"facts-must-round-trip-exactly-or-fail-closed"}
def projection_ref():return ProjectionRef(PROJECTION_ID,PROJECTION_VERSION,_sha(_j(_payload())))
def exact_context():
 a=e3.build_catalog();b=e4.current_schema_ref()
 return ProjectionContext(projection_ref(),a.schema_id,a.version,a.fingerprint,b.schema_id,b.semantic_version,b.content_fingerprint,e5.TARGET_SCHEMA_ID,e5.TARGET_VERSION,e5.TARGET_SCHEMA_FINGERPRINT,e5.OLD_SCHEMA_ID,e5.OLD_VERSION,e5.OLD_SCHEMA_FINGERPRINT)
def _context(c):
 if c!=exact_context():raise ProjectionError("schema-context-mismatch","exact E3/E4/E5/projection identities are required")
 e4.require_schema(e4.SchemaRef(c.e4_schema_id,c.e4_schema_version,c.e4_schema_fingerprint))
def _rows():
 got={x.normalization_row for x in e3.build_catalog().enabled_shapes() if x.normalization_row};want=set(e5.ROW_IDS)
 if got!=want or set(e5.FACT_COMPLETE_ROW_IDS)!=want:raise ProjectionError("authority-row-mismatch","E3 normalization rows and E5 fact-complete rows differ")
 return frozenset(got)
def _bind(v):
 if isinstance(v,bool):return "true" if v else "false"
 if isinstance(v,(tuple,list)):return ", ".join(_bind(x) for x in v)
 return str(v)

def _class(items):
 candidates=(" ","\t","a","A","0","_",".","-",'"');neg=any(op is C.NEGATE for op,_ in items)
 def ok(ch):
  hit=False
  for op,arg in items:
   if op is C.NEGATE:continue
   if op is C.LITERAL:hit|=ord(ch)==arg
   elif op is C.RANGE:hit|=arg[0]<=ord(ch)<=arg[1]
   elif op is C.CATEGORY:
    if arg is C.CATEGORY_SPACE:hit|=ch.isspace()
    elif arg is C.CATEGORY_DIGIT:hit|=ch.isdigit()
    elif arg is C.CATEGORY_WORD:hit|=ch=="_" or ch.isalnum()
    else:raise ProjectionError("regex-render-unsupported",repr(arg))
   else:raise ProjectionError("regex-render-unsupported",repr(op))
  return not hit if neg else hit
 for x in candidates:
  if ok(x):return x
 raise ProjectionError("regex-render-unsupported","no deterministic character-class witness")
def _render(pattern,bindings:Mapping[str,Any]):
 names={n:k for k,n in pattern.groupindex.items()}
 def go(seq):
  out=[]
  for op,arg in seq:
   if op in {C.AT,C.ASSERT,C.ASSERT_NOT}:continue
   if op is C.LITERAL:out.append(chr(arg))
   elif op is C.SUBPATTERN:
    group,_,_,child=arg;name=names.get(group)
    if name is not None:
     if bindings.get(name) is None:raise ProjectionError("missing-inverse-fact",f"missing E5 regex group {name}")
     out.append(_bind(bindings[name]))
    else:out.append(go(child))
   elif op in {C.MAX_REPEAT,C.MIN_REPEAT}:minimum,_,child=arg;out.append(go(child)*minimum)
   elif op is C.IN:out.append(_class(arg))
   elif op is C.BRANCH:
    _,branches=arg
    if not branches:raise ProjectionError("regex-render-unsupported","empty branch")
    out.append(go(branches[0]))
   elif op is C.CATEGORY:out.append(" " if arg is C.CATEGORY_SPACE else "0" if arg is C.CATEGORY_DIGIT else "a" if arg is C.CATEGORY_WORD else (_ for _ in ()).throw(ProjectionError("regex-render-unsupported",repr(arg))))
   elif op is C.ANY:out.append("a")
   else:raise ProjectionError("regex-render-unsupported",repr(op))
  return "".join(out)
 return go(RP.parse(pattern.pattern,pattern.flags))

def _ws(child):
 if len(child)!=1:return False
 op,arg=child[0]
 if op is C.LITERAL:return chr(arg) in {" ","\t"}
 if op is C.IN:return bool(arg) and all(x is C.LITERAL and chr(y) in {" ","\t"} for x,y in arg)
 return False
def _atoms(pattern):
 names={n:k for k,n in pattern.groupindex.items()};out=[]
 for op,arg in RP.parse(pattern.pattern,pattern.flags):
  if op is C.AT:out.append(("AT",arg))
  elif op is C.LITERAL:out.append(("LIT",chr(arg)))
  elif op is C.SUBPATTERN:
   group,_,_,child=arg;name=names.get(group);out.append(("GROUP",name) if name else ("OTHER",repr(tuple(child))))
  elif op in {C.MAX_REPEAT,C.MIN_REPEAT}:
   minimum,maximum,child=arg;out.append(("WS",(minimum,maximum)) if _ws(child) else ("OTHER",repr((op,arg))))
  elif op is C.IN and _ws(((op,arg),)):out.append(("WS",(1,1)))
  else:out.append(("OTHER",repr((op,arg))))
 return tuple(out)
def _same(a,b):return a[0]==b[0] and (a[0] in {"GROUP","WS"} or a==b)
def _sentinel(rule):
 cand,old=_atoms(rule.candidate_re),_atoms(rule.old_re);i=next((i for i,p in enumerate(zip(cand,old)) if not _same(*p)),min(len(cand),len(old)))
 if i>=len(cand):raise ProjectionError("authority-rule-mismatch",f"no candidate sentinel for {rule.row_id}")
 end=i+1
 if cand[i][0]=="LIT" and str(cand[i][1]).isalnum():
  while end<len(cand) and cand[end][0]=="LIT" and (str(cand[end][1]).isalnum() or cand[end][1]=="_"):end+=1
  if end<len(cand) and cand[end][0]=="WS":end+=1
 parts=[]
 for kind,v in cand[:end]:
  if kind=="AT":parts.append("^")
  elif kind=="LIT":parts.append(re.escape(str(v)))
  elif kind=="GROUP":parts.append(r"[ \t]*" if v=="i" else r"[^\n]*?")
  elif kind=="WS":parts.append(r"[ \t]+" if v[0] else r"[ \t]*")
  else:raise ProjectionError("authority-rule-mismatch",f"sentinel op for {rule.row_id}: {v}")
 return re.compile("".join(parts),re.MULTILINE)
def _sentinels(source,matches):
 starts={m.start() for _,m in matches}
 for r in e5.RULES:
  for m in _sentinel(r).finditer(source):
   if m.start() not in starts:raise ProjectionError("incomplete-candidate-anchor",f"incomplete {r.row_id} candidate anchor")
def _header_cardinality(source,matches):
 header={r.row_id for r in e5.RULES if r.role=="declaration-header"};shapes={s.normalization_row:s for s in e3.build_catalog().enabled_shapes() if s.normalization_row in header};starts={m.start():r.row_id for r,m in matches if r.row_id in header}
 if not starts:return
 program,_,_=e5.parse_text(source)
 for node in program.children:
  span=getattr(node,"span",None)
  if span is None or span.offset not in starts:continue
  row=starts[span.offset];shape=shapes.get(row)
  if shape is None:raise ProjectionError("authority-row-mismatch",f"no E3 header shape for {row}")
  counts={c.key:0 for c in shape.keyed_children}
  for n in getattr(node,"children",()):
   m=re.match(r"^([A-Za-z_]\w*)\s*:\s*",(getattr(n,"name",None) or "").strip())
   if m and m.group(1) in counts:counts[m.group(1)]+=1
  for c in shape.keyed_children:
   if c.cardinality is e3.Cardinality.ONE and counts[c.key]!=1:raise ProjectionError("missing-inverse-fact" if counts[c.key]==0 else "ambiguous-inverse-fact",f"{row} requires exactly one {c.key}")
def _unmodeled_e3(source):
 ref=e4.current_schema_ref();svc=e4.CompilerSchemaService();detailed=set(svc.declaration_kinds(ref));shapes={s.kind:s for s in e3.build_catalog().enabled_shapes()};program,_,_=e5.parse_text(source)
 for node in program.children:
  shape=shapes.get(getattr(node,"kind",""))
  if shape is None or shape.normalization_row is not None or shape.kind not in detailed:continue
  span,end=getattr(node,"span",None),getattr(node,"end",None)
  if span is None or end is None or end.offset<=span.offset:continue
  try:parsed=e3.parse_candidate(source[span.offset:end.offset],source_version=e3.build_catalog().version,schema_version=e3.build_catalog().version)
  except e3.ConstructionError:continue
  current={x.slot_id for x in svc.declaration(ref,shape.kind).body_slots}
  if set(parsed.node.values)-current:raise ProjectionError("unsupported-candidate-construct",f"E3 {shape.kind} has no E5 inverse authority")
def _apply(source,edits):
 cursor=0;out=[]
 for start,end,replacement in sorted(edits):
  if start<cursor:raise ProjectionError("ambiguous-inverse","overlapping E5 candidate anchors")
  out.extend((source[cursor:start],replacement));cursor=end
 out.append(source[cursor:]);return "".join(out)
def _mkwargs(s):return dict(source_version=e5.OLD_VERSION,old_version=e5.OLD_VERSION,target_version=e5.TARGET_VERSION,source_schema_fingerprint=e5.OLD_SCHEMA_FINGERPRINT,target_schema_fingerprint=e5.TARGET_SCHEMA_FINGERPRINT,expected_source_fingerprint=e5.source_fingerprint(s))

def project_source(source,*,context):
 _context(context);supported=_rows();matches=tuple(e5._matches(source,candidate=True));legacy=tuple(e5._matches(source,candidate=False))
 if legacy:raise ProjectionError("legacy-spelling-in-candidate-context",f"current spelling for {legacy[0][0].row_id}")
 _sentinels(source,matches);_header_cardinality(source,matches);_unmodeled_e3(source)
 try:facts=e5.extract_facts(source,source_version=e5.TARGET_VERSION)
 except e5.MigrationError as x:raise ProjectionError("e5-candidate-fact-rejected",f"{x.diagnostic.code}: {x.diagnostic.message}") from x
 rows=tuple(r.row_id for r,_ in matches)
 if any(x not in supported for x in rows):raise ProjectionError("unsupported-candidate-row","row lacks E3/E5 fact-complete authority")
 edits=[]
 for r,m in matches:
  try:f=e5._fact(r,m,source,candidate=True)
  except e5.MigrationError as x:raise ProjectionError("e5-candidate-fact-rejected",f"{x.diagnostic.code}: {x.diagnostic.message}") from x
  b={k:v for k,v in m.groupdict().items() if v is not None}
  for k,v in f.facts:b.setdefault(k,v)
  replacement=_render(r.old_re,b)
  if r.old_re.fullmatch(replacement) is None:raise ProjectionError("inverse-witness-invalid",f"E5 old pattern rejected witness for {r.row_id}")
  edits.append((m.start(),m.end(),replacement))
 projected=_apply(source,edits);current=e5.extract_facts(projected,source_version=e5.OLD_VERSION)
 if current!=facts:raise ProjectionError("semantic-fact-mismatch","E5 current/candidate facts differ")
 try:
  canonical=e5.format_candidate(source,source_version=e5.TARGET_VERSION,schema_fingerprint=e5.TARGET_SCHEMA_FINGERPRINT);forward=e5.migrate(projected,**_mkwargs(projected)).source
 except e5.MigrationError as x:raise ProjectionError("e5-roundtrip-rejected",f"{x.diagnostic.code}: {x.diagnostic.message}") from x
 if forward!=canonical:raise ProjectionError("non-lossless-roundtrip","E5 forward migration did not reproduce canonical candidate")
 return SourceProjection(e5.source_fingerprint(source),e5.source_fingerprint(projected),rows,facts,current,projected)

def _compiler_json(stdout,command):
 try:p=json.loads(stdout)
 except json.JSONDecodeError as x:raise ProjectionError("compiler-protocol-error",f"aidl {command} malformed JSON: {x}") from x
 if not isinstance(p,dict) or p.get("command")!=command or not isinstance(p.get("ok"),bool) or not isinstance(p.get("diagnostics",[]),list):raise ProjectionError("compiler-protocol-error",f"aidl {command} response identity invalid")
 return p
def _cmd(root,command):
 argv=(sys.executable,str(ROOT/"aidl"),command,str(root),"--format","json");p=subprocess.run(argv,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);j=_compiler_json(p.stdout,command);expected=0 if j["ok"] else 1
 if p.returncode!=expected:raise ProjectionError("compiler-protocol-error",f"aidl {command} exit {p.returncode} disagrees with ok={j['ok']}")
 return CompilerCommandEvidence(command,tuple(map(str,argv)),p.returncode,bool(j["ok"]),tuple(copy.deepcopy(j.get("diagnostics",[]))),copy.deepcopy(j.get("result")),_sha(p.stdout),p.stderr)
def compiler_evidence(root):
 root=Path(root).resolve();return CompilerEvidence(_cmd(root,"check"),_cmd(root,"ir"))
def project_worktree(candidate_root,output_root,*,context):
 _context(context);candidate_root=Path(candidate_root).resolve();output_root=Path(output_root).resolve()
 if not candidate_root.is_dir():raise ProjectionError("invalid-worktree",f"missing candidate root {candidate_root}")
 if output_root.exists():raise ProjectionError("invalid-output",f"output exists {output_root}")
 output_root.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix="aidl-m16-projection-",dir=output_root.parent) as tmp:
  stage=Path(tmp)/"projected";shutil.copytree(candidate_root,stage,symlinks=True);files=[]
  for p in sorted(x for x in stage.rglob("*.aidl") if x.is_file()):
   rel=p.relative_to(stage).as_posix()
   try:s=p.read_text(encoding="utf-8")
   except UnicodeDecodeError as x:raise ProjectionError("invalid-source-encoding",f"{rel}: UTF-8 required") from x
   q=project_source(s,context=context);p.write_text(q.source,encoding="utf-8");files.append((rel,q))
  evidence=compiler_evidence(stage)
  if not evidence.accepted:raise ProjectionError("compiler-rejected","unchanged production aidl check/aidl ir rejected projected current worktree",evidence=evidence)
  os.replace(stage,output_root)
 return ProjectProjection(context.projection_ref,str(output_root),tuple(files),evidence)
