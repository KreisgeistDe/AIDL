"""M16.5 E4 bounded read-only compiler schema/introspection prototype.

Experimental metadata only. It does not parse, accept, rewrite, or format AIDL source.
"""
from __future__ import annotations
import argparse, hashlib, json
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Iterable

BASE_COMMIT="49866a14d263c9dbf4269f46642d7e86936114cf"
GRAMMAR_BLOB_SHA="834629dab9198c1e78090e31a5ce2a29180a05f1"
SCHEMA_ID="urn:aidl:schema:meta:m16.5-e4-introspection"
SCHEMA_VERSION="0.2.0-e4"
class SchemaLookupError(ValueError):
    def __init__(self,reason,detail): super().__init__(f"{reason}: {detail}"); self.reason=reason; self.detail=detail
@dataclass(frozen=True)
class SchemaRef: schema_id:str; semantic_version:str; content_fingerprint:str
@dataclass(frozen=True)
class ValueShape:
    shape_id:str; kind:str; syntax:str; documentation:str; closed_values:tuple[str,...]=(); item_shape:str|None=None; alternatives:tuple[str,...]=()
@dataclass(frozen=True)
class ModifierShape: modifier_id:str; visible_tokens:tuple[str,...]; value_shape:str|None; documentation:str
@dataclass(frozen=True)
class HeaderArgument: argument_id:str; visible_tokens:tuple[str,...]; value_shape:str; cardinality:str; documentation:str
@dataclass(frozen=True)
class BodySlot:
    slot_id:str; visible_tokens:tuple[str,...]; cardinality:str; value_shape:str|None; documentation:str; name_shape:str|None=None; modifiers:tuple[str,...]=(); nested_schema:str|None=None; semantic_order:str="preserve"
@dataclass(frozen=True)
class DeclarationShape:
    kind:str; family:str; starter_tokens:tuple[str,...]; identity_shape:str; header_arguments:tuple[HeaderArgument,...]; body_slots:tuple[BodySlot,...]; documentation:str; annotations_allowed:bool=True; body_semantic_order:str="preserve"
@dataclass(frozen=True)
class SublanguageAlternative: alternative_id:str; syntax:str; child_schema:str|None=None
@dataclass(frozen=True)
class SublanguageShape:
    name:str; generic_production:str; alternatives:tuple[SublanguageAlternative,...]; vocabulary_authority:str; vocabulary_scope:str; closed_vocabulary:bool; documentation:str; recursive:bool=False; vocabulary:tuple[str,...]=(); semantic_fact_prefixes:tuple[str,...]=()
@dataclass(frozen=True)
class ConstructionSurface:
    surface_id:str; semantic_fact_prefixes:tuple[str,...]; documentation:str; authority:str="e4-compiler-schema"; fact_complete:bool=True
@dataclass(frozen=True)
class IntrospectionCatalog:
    schema_ref:SchemaRef; source_base_commit:str; source_grammar_blob_sha:str; declarations:tuple[DeclarationShape,...]; value_shapes:tuple[ValueShape,...]; modifiers:tuple[ModifierShape,...]; sublanguages:tuple[SublanguageShape,...]; construction_surfaces:tuple[ConstructionSurface,...]; coverage:tuple[str,...]; omissions:tuple[str,...]
    def declaration(self,kind):
        for x in self.declarations:
            if x.kind==kind:return x
        raise KeyError(kind)
    def value_shape(self,shape_id):
        for x in self.value_shapes:
            if x.shape_id==shape_id:return x
        raise KeyError(shape_id)
    def modifier(self,modifier_id):
        for x in self.modifiers:
            if x.modifier_id==modifier_id:return x
        raise KeyError(modifier_id)
    def sublanguage(self,name):
        for x in self.sublanguages:
            if x.name==name:return x
        raise KeyError(name)
    def construction_surface(self,surface_id):
        for x in self.construction_surfaces:
            if x.surface_id==surface_id:return x
        raise KeyError(surface_id)

def _values():
    d="docs/06-grammar.md"
    return (
      ValueShape("identifier","lexical","identifier",d), ValueShape("typeName","lexical","typeName",d), ValueShape("type","type","type",d), ValueShape("expression","expression","expression",d), ValueShape("integer","literal","integer",d), ValueShape("duration","literal","durationLiteral",d),
      ValueShape("delete-action","enum","deleteAction",d,("restrict","cascade","nullify")), ValueShape("profilePropertyValue","generic-value","profilePropertyValue",d), ValueShape("typeName-list","list","[ typeName { , typeName } ]",d,item_shape="typeName"),
      ValueShape("typed-exposed-list","list","[ exposedItem { , exposedItem } ]",d,alternatives=("query qualifiedName","mutation qualifiedName","channel qualifiedName","sync qualifiedName")), ValueShape("typed-runnable-list","list","[ runnableItem { , runnableItem } ]",d,alternatives=("consumer qualifiedName","workflow qualifiedName","task qualifiedName","schedule qualifiedName","projection qualifiedName","sync qualifiedName","channel qualifiedName")),
      ValueShape("app-profile","compound","identifier version integer",d), ValueShape("compatibility-mode","enum","identifier",d,("none","backward","forward","full")), ValueShape("index-fields","compound-list","( indexField { , indexField } )",d), ValueShape("sync-mode","enum","syncMode",d,("serverAuthoritative","queuedCommands","replicated")), ValueShape("sync-authority","enum","syncAuthority",d,("server","serverValidated","merge")), ValueShape("sync-changes-outbox","compound","to typeName via outbox",d), ValueShape("sync-delete-tombstone","compound","tombstone retain durationLiteral",d), ValueShape("sync-schema-migration","literal","required",d,("required",)), ValueShape("profilePropertyValue+","sequence","profilePropertyValue { profilePropertyValue }",d,item_shape="profilePropertyValue")
    )
def _modifiers():
    d="docs/06-grammar.md#Typdeklarationen"
    return tuple(ModifierShape(x,(x,),v,d) for x,v in (("required",None),("primary",None),("generated",None),("clientGenerated",None),("immutable",None),("mutable",None),("sensitive",None),("unique",None),("concurrencyToken",None),("default","expression"),("onDelete","delete-action"),("via","identifier")))
def _field_modifier_ids(): return tuple(x.modifier_id for x in _modifiers())
def _declarations():
    d="docs/06-grammar.md"
    return (
      DeclarationShape("app","App",("app",),"typeName",(),(BodySlot("profile",("profile",),"many","app-profile",d),BodySlot("system",("system",),"many","typeName",d),BodySlot("frontend",("frontend",),"many","typeName",d),BodySlot("api",("api",),"many","typeName",d),BodySlot("defaultDeployment",("defaultDeployment",),"many","identifier",d),BodySlot("compatibility",("compatibility",),"many","identifier",d)),d),
      DeclarationShape("entity","Core",("entity",),"typeName",(),(BodySlot("field",(),"many","type",d,name_shape="identifier",modifiers=_field_modifier_ids()),BodySlot("index",("index",),"many","index-fields",d,name_shape="identifier"),BodySlot("invariant",("invariant",),"many","expression",d,name_shape="identifier")),d),
      DeclarationShape("service","Backend",("service",),"typeName",(),(BodySlot("owns",("owns",),"many","typeName-list",d),BodySlot("uses",("uses",),"many","typeName-list",d),BodySlot("exposes",("exposes",),"many","typed-exposed-list",d),BodySlot("runs",("runs",),"many","typed-runnable-list",d),BodySlot("dependsOn",("dependsOn",),"many","typeName-list",d),BodySlot("reliability",("reliability",),"many",None,d,nested_schema="profileProperty"),BodySlot("telemetry",("telemetry",),"many","identifier",d)),d),
      DeclarationShape("sync","Sync",("sync",),"typeName",(HeaderArgument("target",("for",),"type","one",d),),(BodySlot("mode",("mode",),"many","sync-mode",d),BodySlot("authority",("authority",),"many","sync-authority",d),BodySlot("scope",("scope",":"),"many","expression",d),BodySlot("localStore",("localStore",),"many","typeName",d),BodySlot("serverStore",("serverStore",),"many","typeName",d),BodySlot("operationLog",("operationLog",),"many",None,d,nested_schema="profileProperty"),BodySlot("push",("push",),"many","profilePropertyValue+",d),BodySlot("pull",("pull",),"many","profilePropertyValue+",d),BodySlot("changes",("changes",),"many","sync-changes-outbox",d),BodySlot("delete",("delete",),"many","sync-delete-tombstone",d),BodySlot("conflict",("conflict",),"many",None,d,nested_schema="conflictRule"),BodySlot("rejected",("rejected",),"many","profilePropertyValue+",d),BodySlot("schemaMigration",("schemaMigration",),"many","sync-schema-migration",d)),d),
    )
def _sublanguages():
    return (
      SublanguageShape(
        "profileProperty", "profileProperty",
        (SublanguageAlternative("path-value","propertyPath [ : ] profilePropertyValue newline"), SublanguageAlternative("path-block","propertyPath { { profileProperty } }","profileProperty")),
        "distributed profile schema", "service.reliability property paths", True,
        "docs/07-distributed-systems.md#system-und-services", True,
        ("idempotencyStore","inboxStore","workflowStore","projectionStore","syncStore"),
        ("reliability",),
      ),
      SublanguageShape(
        "uiStatement", "uiStatement",
        (SublanguageAlternative("statement","identifier { uiAtom } [ { { uiStatement } } ] newline","uiStatement"),),
        "web profile schema", "typed UI statement identifiers and atoms", True,
        "docs/03-frontend.md", True,
        ("semantic","layout","image","heading","button","list","repeat","render","grid","form","field","validate","submit","pending","success","failure","optimistic","rollback","conflict","rejected","show","navigate"),
        ("ui",),
      ),
      SublanguageShape(
        "testStatement", "testStatement",
        (SublanguageAlternative("leaf","identifier { expression | qualifiedName | profilePropertyValue } newline"), SublanguageAlternative("block","identifier { expression | qualifiedName } { { testStatement } }","testStatement")),
        "test profile schema", "typed test verbs and operands", True,
        "docs/05-diagnostics-testing.md#testarten", True,
        ("arrange","as","visit","fill","submit","assert","parallel","call","crashpoint","restart","deliver","duplicate","clients","disconnect","on","connect","sync","clientVersion","serverVersion","deploy","run"),
        ("testCall","testAssert"),
      ),
      SublanguageShape(
        "conflictRule", "conflictRule",
        (SublanguageAlternative("field","field identifier merge mergeStrategy newline"), SublanguageAlternative("group","group identifier fields [ identifier { , identifier } ] merge mergeStrategy newline")),
        "standard language schema", "offline-sync conflict rules", True,
        "docs/06-grammar.md#offline-synchronisation", False,
        ("field","group","reject","serverWins","lww","max","min","addWinsSet","removeWinsSet","counter","manual","custom"),
        ("conflict",),
      ),
    )
def _surface(s,*facts): return ConstructionSurface(s,tuple(facts),"docs/06-grammar.md")
def _construction_surfaces():
    return (
      _surface("entity","entity"), _surface("field","field","type","modifier","optional","preserve"), _surface("value","value"), _surface("enum","enum","enumCase"), _surface("invariant","invariant","predicate"), _surface("alias","alias","aliasTarget"),
      _surface("app","app","profile","system","defaultDeployment","frontend","api","preserve"), _surface("service","service","owns","uses","exposes","dependsOn","reliability","preserve"), _surface("system","system","services","resources"),
      _surface("topic","topic","events","delivery","retention","preserve"), _surface("queue","queue","delivery"), _surface("consumer","consumer","topic","source"),
      _surface("workflow","workflow","step","budgetDuration","preserve"), _surface("schedule","schedule","task","cadence"), _surface("schedule-lease","schedule","task"), _surface("task","task","call"),
      _surface("sync","sync","target","authority","mode","localStore","conflict"), _surface("conflictRule","conflict"),
      _surface("api","api","transport","operation","preserve"), _surface("query","query","returns","timeout","preserve"), _surface("mutation","mutation","input","returns"),
      _surface("frontend","frontend","ui"), _surface("page","page","ui"), _surface("test","test"),
    )
def _unsigned_payload():
    return {"schema_id":SCHEMA_ID,"semantic_version":SCHEMA_VERSION,"source_base_commit":BASE_COMMIT,"source_grammar_blob_sha":GRAMMAR_BLOB_SHA,"declarations":[asdict(x) for x in _declarations()],"value_shapes":[asdict(x) for x in _values()],"modifiers":[asdict(x) for x in _modifiers()],"sublanguages":[asdict(x) for x in _sublanguages()],"construction_surfaces":[asdict(x) for x in _construction_surfaces()],"coverage":["representative current declaration metadata remains read-only","bounded compiler-owned construction-surface semantic fact projections from normative grammar/profile contracts","closed profileProperty/uiStatement/testStatement vocabularies sourced from normative profile documentation","exact schema tuple and fail-closed lookup"],"omissions":["not a production parser or language adoption surface","not a complete production 49-form completion schema","generic sublanguage vocabularies are bounded to terms explicitly documented by their normative profile sources, not inferred from evaluation tasks","does not alter production IDE, diagnostics, formatter, compatibility, IR, runtime or generator behavior"]}
def _fingerprint(payload): return "sha256:"+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
@lru_cache(maxsize=1)
def build_catalog():
    p=_unsigned_payload(); return IntrospectionCatalog(SchemaRef(SCHEMA_ID,SCHEMA_VERSION,_fingerprint(p)),BASE_COMMIT,GRAMMAR_BLOB_SHA,_declarations(),_values(),_modifiers(),_sublanguages(),_construction_surfaces(),tuple(p["coverage"]),tuple(p["omissions"]))
def current_schema_ref(): return build_catalog().schema_ref
def require_schema(ref):
    c=build_catalog()
    if ref.schema_id!=c.schema_ref.schema_id: raise SchemaLookupError("unknown-schema-id",ref.schema_id)
    if ref.semantic_version!=c.schema_ref.semantic_version: raise SchemaLookupError("stale-schema-version",ref.semantic_version)
    if ref.content_fingerprint!=c.schema_ref.content_fingerprint: raise SchemaLookupError("fingerprint-mismatch",ref.content_fingerprint)
    return c
class CompilerSchemaService:
    def schema_ref(self): return current_schema_ref()
    def declaration_kinds(self,ref,*,family=None): return tuple(x.kind for x in require_schema(ref).declarations if family is None or x.family==family)
    def declaration(self,ref,kind):
        try:return require_schema(ref).declaration(kind)
        except KeyError as e: raise SchemaLookupError("unknown-declaration-kind",kind) from e
    def sublanguage(self,ref,name):
        try:return require_schema(ref).sublanguage(name)
        except KeyError as e: raise SchemaLookupError("unknown-sublanguage",name) from e
    def value_shape(self,ref,shape_id):
        try:return require_schema(ref).value_shape(shape_id)
        except KeyError as e: raise SchemaLookupError("unknown-value-shape",shape_id) from e
    def modifiers(self,ref,modifier_ids:Iterable[str]):
        c=require_schema(ref); out=[]
        for mid in modifier_ids:
            try:out.append(c.modifier(mid))
            except KeyError as e: raise SchemaLookupError("unknown-modifier",mid) from e
        return tuple(out)
    def construction_surface(self,ref,surface_id):
        try:return require_schema(ref).construction_surface(surface_id)
        except KeyError as e: raise SchemaLookupError("unknown-construction-surface",surface_id) from e
    def construction_surfaces(self,ref): return require_schema(ref).construction_surfaces
    def export(self,ref):
        c=require_schema(ref); return {"schema_ref":asdict(c.schema_ref),"source_base_commit":c.source_base_commit,"source_grammar_blob_sha":c.source_grammar_blob_sha,"declarations":[asdict(x) for x in c.declarations],"value_shapes":[asdict(x) for x in c.value_shapes],"modifiers":[asdict(x) for x in c.modifiers],"sublanguages":[asdict(x) for x in c.sublanguages],"construction_surfaces":[asdict(x) for x in c.construction_surfaces],"coverage":list(c.coverage),"omissions":list(c.omissions)}
def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True); sub.add_parser("schema-ref"); a=p.parse_args(argv); print(json.dumps(asdict(current_schema_ref()),indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
