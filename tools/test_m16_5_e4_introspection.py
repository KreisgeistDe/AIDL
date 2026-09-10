from __future__ import annotations
import dataclasses,json,pathlib,unittest
import tools.m16_5_e4_introspection as e4
from tools.m16_5_e4_introspection import CompilerSchemaService,SchemaLookupError,SchemaRef
ROOT=pathlib.Path(__file__).resolve().parents[1]; CASES=json.loads((ROOT/"fixtures/m16-5/e4-introspection-cases.json").read_text())
class E4IntrospectionTests(unittest.TestCase):
 def setUp(self): self.service=CompilerSchemaService(); self.ref=self.service.schema_ref()
 def test_schema_identity_is_exact_deterministic_and_qualified(self):
  self.assertEqual((self.ref.schema_id,self.ref.semantic_version,self.ref.content_fingerprint),(CASES["schema_id"],CASES["schema_version"],CASES["schema_fingerprint"])); e4.build_catalog.cache_clear(); self.assertEqual(self.ref,self.service.schema_ref()); self.assertEqual(e4.build_catalog().source_base_commit,CASES["source_base_commit"])
 def test_old_e4_tuple_is_stale_and_fails_closed(self):
  with self.assertRaises(SchemaLookupError) as c:self.service.declaration_kinds(SchemaRef(self.ref.schema_id,"0.1.0-e4","sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542"))
  self.assertEqual(c.exception.reason,"stale-schema-version")
 def test_representative_app_core_backend_sync_discover_shapes(self):
  for case in CASES["representative_clients"]:
   s=self.service.declaration(self.ref,case["kind"]); self.assertEqual(s.family,case["family"]); self.assertEqual([x.argument_id for x in s.header_arguments],case["header_arguments"]); self.assertEqual([x.slot_id for x in s.body_slots],case["body_slots"])
 def test_entity_field_shape_exposes_keywordless_entry_and_all_modifiers(self):
  field=next(x for x in self.service.declaration(self.ref,"entity").body_slots if x.slot_id=="field"); self.assertEqual(field.visible_tokens,()); self.assertEqual(len(self.service.modifiers(self.ref,field.modifiers)),12)
 def test_sync_exports_current_compound_forms_not_e3_candidate_syntax(self):
  sync=self.service.declaration(self.ref,"sync"); self.assertEqual(sync.header_arguments[0].visible_tokens,("for",)); self.assertEqual(self.service.value_shape(self.ref,next(x for x in sync.body_slots if x.slot_id=="changes").value_shape).syntax,"to typeName via outbox"); legal=self.service.declaration_kinds(self.ref); [self.assertNotIn(x,legal) for x in CASES["candidate_kinds_that_must_not_be_exported_as_legal"]]
 def test_generic_sublanguages_export_concrete_closed_vocabulary(self):
  for name in CASES["generic_sublanguages"]:
   s=self.service.sublanguage(self.ref,name); self.assertTrue(s.closed_vocabulary); self.assertTrue(s.vocabulary); self.assertTrue(set(CASES["required_vocab"][name]).issubset(s.vocabulary))
 def test_construction_surfaces_are_generic_not_task_keyed(self):
  surfaces=self.service.construction_surfaces(self.ref); ids={x.surface_id for x in surfaces}; self.assertTrue({"value","enum","alias","topic","queue","workflow","schedule","task","api","query","mutation","frontend","page","test"}.issubset(ids)); self.assertFalse(any(x.surface_id.startswith("m16-") for x in surfaces)); self.assertIn("testAssert",self.service.sublanguage(self.ref,"testStatement").semantic_fact_prefixes)
 def test_unknown_stale_or_mismatched_schema_fails_closed(self):
  for bad in (SchemaRef("other",self.ref.semantic_version,self.ref.content_fingerprint),SchemaRef(self.ref.schema_id,"stale",self.ref.content_fingerprint),SchemaRef(self.ref.schema_id,self.ref.semantic_version,"sha256:"+"0"*64)):
   with self.assertRaises(SchemaLookupError):self.service.declaration_kinds(bad)
 def test_nesting_and_value_references_resolve(self):
  c=e4.require_schema(self.ref)
  for d in c.declarations:
   for s in d.body_slots:
    if s.value_shape:self.service.value_shape(self.ref,s.value_shape)
    if s.nested_schema:self.service.sublanguage(self.ref,s.nested_schema)
    for m in self.service.modifiers(self.ref,s.modifiers):
     if m.value_shape:self.service.value_shape(self.ref,m.value_shape)
 def test_catalog_is_read_only_and_export_deterministic(self):
  c=e4.require_schema(self.ref)
  with self.assertRaises(dataclasses.FrozenInstanceError): c.schema_ref.semantic_version="x"
  self.assertEqual(self.service.export(self.ref),self.service.export(self.ref)); self.assertFalse(hasattr(self.service,"register")); self.assertFalse(hasattr(self.service,"update"))
 def test_unknown_lookup_fails_explicitly(self):
  for fn in (lambda:self.service.declaration(self.ref,"mystery"),lambda:self.service.sublanguage(self.ref,"mystery"),lambda:self.service.value_shape(self.ref,"mystery"),lambda:self.service.construction_surface(self.ref,"mystery")):
   with self.assertRaises(SchemaLookupError):fn()
 def test_prototype_does_not_import_production_parser_or_e3_parser(self):
  source=pathlib.Path(e4.__file__).read_text(); self.assertNotIn("tools.aidl_parser",source); self.assertNotIn("m16_5_e3_prototype",source)
if __name__=="__main__":unittest.main()
