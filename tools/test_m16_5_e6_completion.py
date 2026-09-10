from __future__ import annotations
import dataclasses, json, pathlib, unittest
import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5
import tools.m16_5_e6_completion as e6
from tools.m16_5_e6_completion import (
    CompletionContextError, CompletionSet, CompletionUnavailable,
    CurrentCompletionContext, E5MigrationCompletionContext,
    ExperimentalCompletionConsumer,
)
ROOT=pathlib.Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'fixtures/m16-5/e6-completion-cases.json').read_text())
MIG=json.loads((ROOT/'fixtures/m16-5/e5-migration-cases.json').read_text())
class E6CompletionTests(unittest.TestCase):
 def setUp(self):
  self.consumer=ExperimentalCompletionConsumer(); self.ref=self.consumer.compiler_schema_ref(); self.current=CurrentCompletionContext(self.ref)
 def migration_context(self,source,source_version=e5.OLD_VERSION):
  x=CASES['e5_context']; old=source_version==e5.OLD_VERSION
  return E5MigrationCompletionContext(x['old_schema_id'],x['old_version'],x['old_schema_fingerprint'],x['target_schema_id'],x['target_version'],x['target_schema_fingerprint'],x['old_schema_id'] if old else x['target_schema_id'],source_version,x['old_schema_fingerprint'] if old else x['target_schema_fingerprint'],e5.source_fingerprint(source))
 def test_exact_e4_schema_tuple(self):
  x=CASES['e4_schema']; self.assertEqual((self.ref.schema_id,self.ref.semantic_version,self.ref.content_fingerprint),(x['schema_id'],x['schema_version'],x['schema_fingerprint']))
 def test_representative_declaration_completion_is_schema_driven(self):
  for family,kind in [('App','app'),('Core','entity'),('Backend','service'),('Sync','sync')]:
   with self.subTest(kind=kind):
    starters=self.consumer.declaration_starters(self.current,family=family); self.assertEqual([x.metadata_id for x in starters.items],[kind]); self.assertTrue(self.consumer.body_slots(self.current,kind).items)
 def test_sync_header_and_closed_values_come_from_e4(self):
  header=self.consumer.header_arguments(self.current,'sync'); self.assertEqual(header.items[0].insert_text,'for'); values=self.consumer.value_candidates(self.current,'sync-mode'); self.assertIsInstance(values,CompletionSet); self.assertEqual([x.insert_text for x in values.items],['serverAuthoritative','queuedCommands','replicated'])
 def test_entity_modifiers_come_from_e4(self):
  values=self.consumer.modifier_candidates(self.current,'entity','field'); self.assertIn('required',[x.metadata_id for x in values.items]); self.assertIn('sensitive',[x.metadata_id for x in values.items]); self.assertEqual(next(x for x in values.items if x.metadata_id=='default').expected_value_shape,'expression')
 def test_keywordless_field_does_not_invent_template(self):
  field=next(x for x in self.consumer.body_slots(self.current,'entity').items if x.metadata_id=='field'); self.assertIsNone(field.insert_text); self.assertEqual(field.expected_name_shape,'identifier'); self.assertEqual(field.expected_value_shape,'type')
 def test_e4_preserve_order_is_not_client_sorted(self):
  body=self.consumer.body_slots(self.current,'service'); self.assertEqual(body.semantic_order,'preserve'); self.assertEqual([x.metadata_id for x in body.items],['owns','uses','exposes','runs','dependsOn','reliability','telemetry'])
 def test_generic_sublanguage_structure_and_vocabulary_are_exported(self):
  for name,required in CASES['generic_vocabulary'].items():
   with self.subTest(name=name):
    self.assertTrue(self.consumer.sublanguage_structure(self.current,name).items); vocab=self.consumer.sublanguage_vocabulary(self.current,name); self.assertIsInstance(vocab,CompletionSet); self.assertTrue(set(required).issubset({x.insert_text for x in vocab.items}))
 def test_profile_vocabulary_provenance_is_not_benchmark_derived(self):
  schema=e4.CompilerSchemaService().sublanguage(self.ref,'profileProperty'); self.assertEqual(schema.documentation,'docs/07-distributed-systems.md#system-und-services'); self.assertIn('projectionStore',schema.vocabulary)
 def test_stale_or_unknown_e4_context_fails_closed(self):
  stale=CurrentCompletionContext(e4.SchemaRef(self.ref.schema_id,'0.1.0-e4','sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542'))
  with self.assertRaises(e4.SchemaLookupError): self.consumer.declaration_starters(stale)
  with self.assertRaises(e4.SchemaLookupError): self.consumer.sublanguage_vocabulary(self.current,'unknown')
 def test_open_value_vocabulary_is_not_reconstructed(self):
  result=self.consumer.value_candidates(self.current,'identifier'); self.assertIsInstance(result,CompletionUnavailable); self.assertEqual(result.reason,'compiler-value-vocabulary-not-exported')
 def test_current_completion_never_emits_candidate_punctuation(self):
  sync=self.consumer.body_slots(self.current,'sync'); changes=next(x for x in sync.items if x.metadata_id=='changes'); self.assertEqual(changes.insert_text,'changes'); self.assertNotEqual(changes.insert_text,'changes:')
 def test_all_nine_e5_migration_rows_are_presented_only_from_dry_run(self):
  for row in MIG['normalization_rows']:
   with self.subTest(row=row['id']):
    source=row['old']; plan=e5.plan_migration(source,source_version=e5.OLD_VERSION,old_version=e5.OLD_VERSION,target_version=e5.TARGET_VERSION,source_schema_fingerprint=e5.OLD_SCHEMA_FINGERPRINT,target_schema_fingerprint=e5.TARGET_SCHEMA_FINGERPRINT,expected_source_fingerprint=e5.source_fingerprint(source)); edit=plan.edits[0]; result=self.consumer.migration_completion(source,edit.start+1,self.migration_context(source)); self.assertIsInstance(result,CompletionSet); self.assertEqual(result.items[0].insert_text,edit.replacement); self.assertEqual(result.items[0].metadata_id,row['id'])
 def test_multi_source_projection_is_now_fact_complete(self):
  source=MIG['multi_source_projection']['old']; result=self.consumer.migration_completion(source,source.index('projection')+1,self.migration_context(source)); self.assertIsInstance(result,CompletionSet); self.assertIn('source: A',result.items[0].insert_text); self.assertIn('source: B',result.items[0].insert_text)
 def test_e5_context_is_exact_no_latest_or_old_candidate_v1(self):
  source=MIG['normalization_rows'][0]['old']; good=self.migration_context(source); bad=(dataclasses.replace(good,target_version='latest'),dataclasses.replace(good,target_version='m16.5-e5-candidate-v1'),dataclasses.replace(good,target_schema_fingerprint='sha256:'+'0'*64))
  for context in bad:
   with self.assertRaises(CompletionContextError): self.consumer.migration_completion(source,source.index('projection')+1,context)
 def test_explicit_target_version_is_noop_not_sniffed_current(self):
  source=MIG['normalization_rows'][1]['candidate']; result=self.consumer.migration_completion(source,source.index('service:'),self.migration_context(source,e5.TARGET_VERSION)); self.assertIsInstance(result,CompletionUnavailable); self.assertEqual(result.reason,'e5-no-modeled-migration-edit')
 def test_source_contains_no_second_language_schema_tables(self):
  source=pathlib.Path(e6.__file__).read_text(); self.assertIn('m16_5_e4_introspection',source); self.assertIn('m16_5_e5_migration',source); self.assertNotIn('ROW_IDS =',source); self.assertNotIn('RULES =',source); self.assertNotIn('aidl_parser',source)
if __name__=='__main__': unittest.main()
