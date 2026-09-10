"""M16.5 E7 bounded diagnostics consumer experiment; not production diagnostics."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5
class DiagnosticsSchemaService(Protocol):
 def schema_ref(self)->e4.SchemaRef:...
 def declaration(self,ref:e4.SchemaRef,kind:str)->e4.DeclarationShape:...
 def sublanguage(self,ref:e4.SchemaRef,name:str)->e4.SublanguageShape:...
 def value_shape(self,ref:e4.SchemaRef,shape_id:str)->e4.ValueShape:...
 def modifiers(self,ref:e4.SchemaRef,modifier_ids:tuple[str,...])->tuple[e4.ModifierShape,...]:...
@dataclass(frozen=True)
class CurrentDiagnosticsContext: schema_ref:e4.SchemaRef
@dataclass(frozen=True)
class E5MigrationDiagnosticsContext:
 old_schema_id:str;old_version:str;old_schema_fingerprint:str;target_schema_id:str;target_version:str;target_schema_fingerprint:str;source_schema_id:str;source_version:str;source_schema_fingerprint:str;expected_source_fingerprint:str;language_state:str
@dataclass(frozen=True)
class SourceLocation:start:int;end:int;line:int;column:int
@dataclass(frozen=True)
class StructuralDiagnostic:
 code:str;phase:str;severity:str;message:str;location:SourceLocation;expected:str|None;authority:str;documentation:str|None=None;replacement:str|None=None;compatibility_class:None=None;migration_authorized:bool=False
@dataclass(frozen=True)
class CompilerSemanticIntent: code:str;phase:str;severity:str;message:str;expected:str|None=None;documentation:str|None=None
@dataclass(frozen=True)
class SemanticDiagnosticProjection:
 code:str;phase:str;severity:str;message:str;location:SourceLocation;expected:str|None;documentation:str|None;source_context:str;authority:str="compiler-semantic-intent";compatibility_class:None=None;migration_authorized:bool=False
@dataclass(frozen=True)
class DiagnosticUnavailable:reason:str;detail:str;authority:str
class DiagnosticsContextError(ValueError):
 def __init__(self,code,detail):super().__init__(f"{code}: {detail}");self.code=code;self.detail=detail
def _location(source,start,end=None):
 end=start if end is None else end
 if start<0 or end<start or end>len(source):raise DiagnosticsContextError("AIDL-S008",f"invalid source range {start}:{end}")
 prev=source.rfind("\n",0,start);return SourceLocation(start,end,source.count("\n",0,start)+1,start+1 if prev<0 else start-prev)
def _slot(shape,slot_id):return next((x for x in shape.body_slots if x.slot_id==slot_id),None)
class ExperimentalDiagnosticsConsumer:
 def __init__(self,service=None):self._service=service or e4.CompilerSchemaService()
 def compiler_schema_ref(self):return self._service.schema_ref()
 @staticmethod
 def order(ds):
  rank={"error":0,"warning":1,"info":2};return tuple(sorted(ds,key=lambda x:(x.location.start,x.phase,rank.get(x.severity,99),x.code,x.message)))
 def unknown_body_slot(self,source,start,end,context,declaration_kind,observed_slot_id):
  s=self._declaration(context,declaration_kind)
  if _slot(s,observed_slot_id):return None
  return StructuralDiagnostic("AIDL-S003","structural-schema","error",f"unknown structural slot {observed_slot_id!r} for {declaration_kind}",_location(source,start,end),", ".join(x.slot_id for x in s.body_slots),"e4-compiler-schema",s.documentation)
 def wrong_closed_value(self,source,start,end,context,shape_id,observed_value):
  s=self._value_shape(context,shape_id)
  if not s.closed_values:return DiagnosticUnavailable("value-validation-not-exported",f"{shape_id} has no closed compiler-owned values in E4 metadata","e4-compiler-schema")
  if observed_value in s.closed_values:return None
  return StructuralDiagnostic("AIDL-S004","structural-schema","error",f"invalid value {observed_value!r} for {shape_id}",_location(source,start,end)," | ".join(s.closed_values),"e4-compiler-schema",s.documentation)
 def invalid_modifier(self,source,start,end,context,declaration_kind,slot_id,observed_modifier):
  s=self._declaration(context,declaration_kind);slot=_slot(s,slot_id)
  if slot is None:return DiagnosticUnavailable("unmodeled-body-slot",f"{declaration_kind}.{slot_id} is not exported by E4","e4-compiler-schema")
  known=tuple(x.modifier_id for x in self._modifiers(context,slot.modifiers))
  if observed_modifier in known:return None
  if not known:return DiagnosticUnavailable("modifier-vocabulary-not-exported",f"{declaration_kind}.{slot_id} has no exported modifier vocabulary","e4-compiler-schema")
  return StructuralDiagnostic("AIDL-S005","structural-schema","error",f"invalid modifier {observed_modifier!r} for {declaration_kind}.{slot_id}",_location(source,start,end)," | ".join(known),"e4-compiler-schema",slot.documentation)
 def invalid_nesting(self,source,start,end,context,declaration_kind,slot_id,observed_nested_schema):
  s=self._declaration(context,declaration_kind);slot=_slot(s,slot_id)
  if slot is None:return DiagnosticUnavailable("unmodeled-body-slot",f"{declaration_kind}.{slot_id} is not exported by E4","e4-compiler-schema")
  if slot.nested_schema is None:return DiagnosticUnavailable("no-nested-schema",f"{declaration_kind}.{slot_id} has no nested schema in E4","e4-compiler-schema")
  self._sublanguage(context,slot.nested_schema)
  if observed_nested_schema==slot.nested_schema:return None
  return StructuralDiagnostic("AIDL-S005","structural-schema","error",f"invalid nested schema {observed_nested_schema!r} for {declaration_kind}.{slot_id}",_location(source,start,end),slot.nested_schema,"e4-compiler-schema",slot.documentation)
 def sublanguage_vocabulary(self,context,name):
  s=self._sublanguage(context,name)
  if not s.closed_vocabulary:raise DiagnosticsContextError("AIDL-S008",f"unexpected open sublanguage vocabulary: {name}")
  if not s.vocabulary:return DiagnosticUnavailable("closed-vocabulary-not-exported",f"{name}: {s.vocabulary_authority}","e4-compiler-schema")
  return s.vocabulary
 def unknown_sublanguage_word(self,source,start,end,context,name,observed):
  s=self._sublanguage(context,name)
  if not s.closed_vocabulary:raise DiagnosticsContextError("AIDL-S008",f"unexpected open sublanguage vocabulary: {name}")
  if not s.vocabulary:return DiagnosticUnavailable("closed-vocabulary-not-exported",f"{name}: {s.vocabulary_authority}","e4-compiler-schema")
  if observed in s.vocabulary:return None
  return StructuralDiagnostic("AIDL-S004","structural-schema","error",f"invalid closed-vocabulary word {observed!r} for {name}",_location(source,start,end)," | ".join(s.vocabulary),"e4-compiler-schema",s.documentation)
 def migration_diagnostic(self,source,offset,context):
  self._require_exact_e5_context(source,context)
  if context.language_state=="legacy":
   if context.source_version!=e5.OLD_VERSION:return DiagnosticUnavailable("explicit-language-state-mismatch","legacy state requires the explicit old E5 source version","e5-migrator")
   return None
  try:p=e5.plan_migration(source,source_version=context.source_version,old_version=context.old_version,target_version=context.target_version,source_schema_fingerprint=context.source_schema_fingerprint,target_schema_fingerprint=context.target_schema_fingerprint,expected_source_fingerprint=context.expected_source_fingerprint)
  except e5.MigrationError as er:
   d=er.diagnostic;st=max(0,min(d.offset,len(source)));return StructuralDiagnostic(d.code,"migration","error",d.message,_location(source,st,min(len(source),st+1)),None,"e5-migrator","docs/m16-5-e5-migration-report.md")
  if not p.edits:return None
  ms=tuple(x for x in p.edits if x.start<=offset<=x.end)
  if len(ms)!=1:return DiagnosticUnavailable("e5-no-unique-edit-at-offset",f"expected one modeled E5 edit at offset {offset}, got {len(ms)}","e5-migrator")
  edit=ms[0]
  if edit.row_id not in p.e3_replayed_rows:return DiagnosticUnavailable("e5-target-shape-not-fact-complete",f"{edit.row_id} is not in E5's E3-replayed fact-complete set","e5-migrator")
  if context.language_state=="coexistence":code,severity,msg="AIDL-S006","warning","legacy spelling is deprecated in the explicit E5 coexistence prototype context"
  else:code,severity,msg="AIDL-S007","error","legacy spelling is invalid in the explicit E5 target prototype context"
  return StructuralDiagnostic(code,"migration",severity,msg,_location(source,edit.start,edit.end),"explicit E5 migration replacement","e5-migrator","docs/m16-5-e2-compatibility-migration-contract.md",edit.replacement)
 def equivalent_semantic_intent(self,old_source,candidate_source,old_offset,context,intent):
  self._require_exact_e5_context(old_source,context)
  if context.source_version!=e5.OLD_VERSION:return DiagnosticUnavailable("equivalence-requires-old-source-context","semantic projection starts from the explicit E5 old source snapshot","e5-migrator")
  try:p=e5.plan_migration(old_source,source_version=context.source_version,old_version=context.old_version,target_version=context.target_version,source_schema_fingerprint=context.source_schema_fingerprint,target_schema_fingerprint=context.target_schema_fingerprint,expected_source_fingerprint=context.expected_source_fingerprint)
  except e5.MigrationError as er:return DiagnosticUnavailable(f"e5-{er.diagnostic.code}",er.diagnostic.message,"e5-migrator")
  ms=tuple(x for x in p.edits if x.start<=old_offset<=x.end)
  if len(ms)!=1:return DiagnosticUnavailable("e5-no-unique-edit-at-offset",f"expected one modeled E5 edit at offset {old_offset}, got {len(ms)}","e5-migrator")
  edit=ms[0]
  if edit.row_id not in p.e3_replayed_rows:return DiagnosticUnavailable("e5-target-shape-not-fact-complete",f"{edit.row_id} is not in E5's E3-replayed fact-complete set","e5-migrator")
  migrated=e5.apply_plan(old_source,p).source
  if migrated!=candidate_source:return DiagnosticUnavailable("candidate-snapshot-mismatch","candidate snapshot must be exactly the E5 dry-run target","e5-migrator")
  rel=next((x for x in p.relocations if x.anchor_id==edit.anchor_id),None)
  if rel is None:return DiagnosticUnavailable("missing-e5-relocation",edit.anchor_id,"e5-migrator")
  return (SemanticDiagnosticProjection(intent.code,intent.phase,intent.severity,intent.message,_location(old_source,edit.start,edit.end),intent.expected,intent.documentation,"explicit-e5-old"),SemanticDiagnosticProjection(intent.code,intent.phase,intent.severity,intent.message,_location(candidate_source,rel.new_start,rel.new_end),intent.expected,intent.documentation,"explicit-e5-target"))
 def _declaration(self,c,k):
  try:return self._service.declaration(c.schema_ref,k)
  except e4.SchemaLookupError as er:raise DiagnosticsContextError("AIDL-S008",f"{er.reason}: {er.detail}") from er
 def _value_shape(self,c,k):
  try:return self._service.value_shape(c.schema_ref,k)
  except e4.SchemaLookupError as er:raise DiagnosticsContextError("AIDL-S008",f"{er.reason}: {er.detail}") from er
 def _modifiers(self,c,ids):
  try:return self._service.modifiers(c.schema_ref,ids)
  except e4.SchemaLookupError as er:raise DiagnosticsContextError("AIDL-S008",f"{er.reason}: {er.detail}") from er
 def _sublanguage(self,c,k):
  try:return self._service.sublanguage(c.schema_ref,k)
  except e4.SchemaLookupError as er:raise DiagnosticsContextError("AIDL-S008",f"{er.reason}: {er.detail}") from er
 @staticmethod
 def _require_exact_e5_context(source,c):
  if c.language_state not in {"legacy","coexistence","target"}:raise DiagnosticsContextError("AIDL-S008",f"unknown explicit language state {c.language_state!r}")
  if c.old_schema_id!=e5.OLD_SCHEMA_ID or c.target_schema_id!=e5.TARGET_SCHEMA_ID:raise DiagnosticsContextError("AIDL-S008","unknown E5 schema identity")
  if c.old_version!=e5.OLD_VERSION or c.target_version!=e5.TARGET_VERSION:raise DiagnosticsContextError("AIDL-S008","unknown or stale E5 version pair")
  if c.old_schema_fingerprint!=e5.OLD_SCHEMA_FINGERPRINT:raise DiagnosticsContextError("AIDL-S008","stale E5 old schema fingerprint")
  if c.target_schema_fingerprint!=e5.TARGET_SCHEMA_FINGERPRINT:raise DiagnosticsContextError("AIDL-S008","stale E5 target schema fingerprint")
  if c.source_version==e5.OLD_VERSION:eid,efp=e5.OLD_SCHEMA_ID,e5.OLD_SCHEMA_FINGERPRINT
  elif c.source_version==e5.TARGET_VERSION:eid,efp=e5.TARGET_SCHEMA_ID,e5.TARGET_SCHEMA_FINGERPRINT
  else:raise DiagnosticsContextError("AIDL-S008",f"unknown E5 source version {c.source_version!r}")
  if c.source_schema_id!=eid:raise DiagnosticsContextError("AIDL-S008","E5 source schema ID mismatch")
  if c.source_schema_fingerprint!=efp:raise DiagnosticsContextError("AIDL-S008","E5 source schema fingerprint mismatch")
  if c.expected_source_fingerprint!=e5.source_fingerprint(source):raise DiagnosticsContextError("AIDL-S008","stale E5 source fingerprint")
