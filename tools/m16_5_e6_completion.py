"""M16.5 E6 bounded IDE/completion consumer experiment; not production IDE behavior."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5
class CompletionSchemaService(Protocol):
 def schema_ref(self)->e4.SchemaRef:...
 def declaration_kinds(self,ref:e4.SchemaRef,*,family:str|None=None)->tuple[str,...]:...
 def declaration(self,ref:e4.SchemaRef,kind:str)->e4.DeclarationShape:...
 def sublanguage(self,ref:e4.SchemaRef,name:str)->e4.SublanguageShape:...
 def value_shape(self,ref:e4.SchemaRef,shape_id:str)->e4.ValueShape:...
 def modifiers(self,ref:e4.SchemaRef,modifier_ids:tuple[str,...])->tuple[e4.ModifierShape,...]:...
@dataclass(frozen=True)
class CurrentCompletionContext: schema_ref:e4.SchemaRef
@dataclass(frozen=True)
class E5MigrationCompletionContext:
 old_schema_id:str; old_version:str; old_schema_fingerprint:str; target_schema_id:str; target_version:str; target_schema_fingerprint:str; source_schema_id:str; source_version:str; source_schema_fingerprint:str; expected_source_fingerprint:str
@dataclass(frozen=True)
class CompletionItem:
 metadata_id:str; kind:str; insert_text:str|None; display_text:str; authority:str; documentation:str|None; expected_name_shape:str|None=None; expected_value_shape:str|None=None; nested_schema:str|None=None; semantic_order:str="preserve"
@dataclass(frozen=True)
class CompletionSet: context:str; items:tuple[CompletionItem,...]; semantic_order:str="preserve"
@dataclass(frozen=True)
class CompletionUnavailable: reason:str; detail:str; authority:str
class CompletionContextError(ValueError):
 def __init__(self,reason,detail):super().__init__(f"{reason}: {detail}");self.reason=reason;self.detail=detail
def _visible_text(tokens):return " ".join(tokens) if tokens else None
def _slot(shape,slot_id):
 for slot in shape.body_slots:
  if slot.slot_id==slot_id:return slot
 raise CompletionContextError("unknown-body-slot",f"{shape.kind}.{slot_id}")
def _item_from_slot(service,ref,slot):
 if slot.value_shape:service.value_shape(ref,slot.value_shape)
 if slot.nested_schema:service.sublanguage(ref,slot.nested_schema)
 ins=_visible_text(slot.visible_tokens)
 return CompletionItem(slot.slot_id,"body-slot",ins,ins or slot.slot_id,"e4-compiler-schema",slot.documentation,slot.name_shape,slot.value_shape,slot.nested_schema,slot.semantic_order)
class ExperimentalCompletionConsumer:
 def __init__(self,service=None):self._service=service or e4.CompilerSchemaService()
 def compiler_schema_ref(self):return self._service.schema_ref()
 def declaration_starters(self,context,*,family=None):
  items=[]
  for kind in self._service.declaration_kinds(context.schema_ref,family=family):
   s=self._service.declaration(context.schema_ref,kind);ins=_visible_text(s.starter_tokens)
   if ins is None:raise CompletionContextError("unmodeled-starter",kind)
   items.append(CompletionItem(s.kind,"declaration-starter",ins,ins,"e4-compiler-schema",s.documentation,s.identity_shape))
  return CompletionSet("current-accepted",tuple(items))
 def header_arguments(self,context,declaration_kind):
  s=self._service.declaration(context.schema_ref,declaration_kind);items=[]
  for a in s.header_arguments:
   self._service.value_shape(context.schema_ref,a.value_shape);ins=_visible_text(a.visible_tokens)
   if ins is None:raise CompletionContextError("unmodeled-header-token",a.argument_id)
   items.append(CompletionItem(a.argument_id,"header-argument",ins,ins,"e4-compiler-schema",a.documentation,expected_value_shape=a.value_shape))
  return CompletionSet("current-accepted",tuple(items))
 def body_slots(self,context,declaration_kind):
  s=self._service.declaration(context.schema_ref,declaration_kind)
  if s.body_semantic_order not in {"preserve","unordered"}:raise CompletionContextError("unknown-semantic-order",f"{s.kind}: {s.body_semantic_order}")
  return CompletionSet("current-accepted",tuple(_item_from_slot(self._service,context.schema_ref,x) for x in s.body_slots),s.body_semantic_order)
 def value_candidates(self,context,shape_id):
  s=self._service.value_shape(context.schema_ref,shape_id)
  if not s.closed_values:return CompletionUnavailable("compiler-value-vocabulary-not-exported",f"{shape_id} has no closed values in E4 metadata","e4-compiler-schema")
  return CompletionSet("current-accepted",tuple(CompletionItem(v,"closed-value",v,v,"e4-compiler-schema",s.documentation,expected_value_shape=s.shape_id) for v in s.closed_values))
 def modifier_candidates(self,context,declaration_kind,slot_id):
  d=self._service.declaration(context.schema_ref,declaration_kind);slot=_slot(d,slot_id);items=[]
  for m in self._service.modifiers(context.schema_ref,slot.modifiers):
   if m.value_shape:self._service.value_shape(context.schema_ref,m.value_shape)
   ins=_visible_text(m.visible_tokens)
   if ins is None:raise CompletionContextError("unmodeled-modifier-token",m.modifier_id)
   items.append(CompletionItem(m.modifier_id,"modifier",ins,ins,"e4-compiler-schema",m.documentation,expected_value_shape=m.value_shape))
  return CompletionSet("current-accepted",tuple(items),slot.semantic_order)
 def nested_structure(self,context,declaration_kind,slot_id):
  slot=_slot(self._service.declaration(context.schema_ref,declaration_kind),slot_id)
  if slot.nested_schema is None:return CompletionUnavailable("no-nested-schema",f"{declaration_kind}.{slot_id} has no nested schema","e4-compiler-schema")
  return self.sublanguage_structure(context,slot.nested_schema)
 def sublanguage_structure(self,context,name):
  s=self._service.sublanguage(context.schema_ref,name)
  if not s.closed_vocabulary:raise CompletionContextError("open-sublanguage-vocabulary",name)
  return CompletionSet("current-accepted",tuple(CompletionItem(a.alternative_id,"sublanguage-structure",None,a.syntax,"e4-compiler-schema",s.documentation,nested_schema=a.child_schema) for a in s.alternatives))
 def sublanguage_vocabulary(self,context,name):
  s=self._service.sublanguage(context.schema_ref,name)
  if not s.closed_vocabulary:raise CompletionContextError("open-sublanguage-vocabulary",name)
  if not s.vocabulary:return CompletionUnavailable("closed-vocabulary-not-exported",f"{name}: {s.vocabulary_authority}","e4-compiler-schema")
  return CompletionSet("current-accepted",tuple(CompletionItem(v,"sublanguage-vocabulary",v,v,"e4-compiler-schema",s.documentation) for v in s.vocabulary))
 def migration_completion(self,source,offset,context):
  self._require_exact_e5_context(source,context)
  try:p=e5.plan_migration(source,source_version=context.source_version,old_version=context.old_version,target_version=context.target_version,source_schema_fingerprint=context.source_schema_fingerprint,target_schema_fingerprint=context.target_schema_fingerprint,expected_source_fingerprint=context.expected_source_fingerprint)
  except e5.MigrationError as er:return CompletionUnavailable(f"e5-{er.diagnostic.code}",er.diagnostic.message,"e5-migrator")
  if not p.edits:return CompletionUnavailable("e5-no-modeled-migration-edit","explicit E5 context produced no migration edit; no candidate syntax is guessed","e5-migrator")
  matches=tuple(x for x in p.edits if x.start<=offset<=x.end)
  if len(matches)!=1:return CompletionUnavailable("e5-no-unique-edit-at-offset",f"expected one modeled migration edit at offset {offset}, got {len(matches)}","e5-migrator")
  edit=matches[0]
  if edit.row_id not in p.e3_replayed_rows:return CompletionUnavailable("e5-target-shape-not-fact-complete",f"{edit.row_id} is not in E5's E3-replayed fact-complete set","e5-migrator")
  return CompletionSet("explicit-e5-target",(CompletionItem(edit.row_id,"migration-replacement",edit.replacement,f"E5 migration: {edit.row_id}","e5-migrator","docs/m16-5-e5-migration-report.md"),))
 @staticmethod
 def _require_exact_e5_context(source,context):
  if context.old_schema_id!=e5.OLD_SCHEMA_ID:raise CompletionContextError("unknown-e5-old-schema-id",context.old_schema_id)
  if context.target_schema_id!=e5.TARGET_SCHEMA_ID:raise CompletionContextError("unknown-e5-target-schema-id",context.target_schema_id)
  if context.old_version!=e5.OLD_VERSION or context.target_version!=e5.TARGET_VERSION:raise CompletionContextError("unknown-e5-version-pair",f"{context.old_version} -> {context.target_version}")
  if context.old_schema_fingerprint!=e5.OLD_SCHEMA_FINGERPRINT:raise CompletionContextError("stale-e5-old-fingerprint",context.old_schema_fingerprint)
  if context.target_schema_fingerprint!=e5.TARGET_SCHEMA_FINGERPRINT:raise CompletionContextError("stale-e5-target-fingerprint",context.target_schema_fingerprint)
  if context.source_version==e5.OLD_VERSION:eid,efp=e5.OLD_SCHEMA_ID,e5.OLD_SCHEMA_FINGERPRINT
  elif context.source_version==e5.TARGET_VERSION:eid,efp=e5.TARGET_SCHEMA_ID,e5.TARGET_SCHEMA_FINGERPRINT
  else:raise CompletionContextError("unknown-e5-source-version",context.source_version)
  if context.source_schema_id!=eid:raise CompletionContextError("e5-source-schema-id-mismatch",context.source_schema_id)
  if context.source_schema_fingerprint!=efp:raise CompletionContextError("e5-source-schema-fingerprint-mismatch",context.source_schema_fingerprint)
  if context.expected_source_fingerprint!=e5.source_fingerprint(source):raise CompletionContextError("stale-e5-source-fingerprint",context.expected_source_fingerprint)
