from __future__ import annotations
import dataclasses, json, pathlib, unittest
import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5
import tools.m16_5_e7_diagnostics as e7
from tools.m16_5_e7_diagnostics import (
    CompilerSemanticIntent, CurrentDiagnosticsContext, DiagnosticUnavailable,
    DiagnosticsContextError, E5MigrationDiagnosticsContext,
    ExperimentalDiagnosticsConsumer, SemanticDiagnosticProjection, StructuralDiagnostic,
)
ROOT=pathlib.Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'fixtures/m16-5/e7-diagnostics-cases.json').read_text())
MIG=json.loads((ROOT/'fixtures/m16-5/e5-migration-cases.json').read_text())
class E7DiagnosticsTests(unittest.TestCase):
 def setUp(self):
  self.consumer=ExperimentalDiagnosticsConsumer(); self.ref=self.consumer.compiler_schema_ref(); self.current=CurrentDiagnosticsContext(self.ref)
 def migration_context(self,source,state='target',source_version=e5.OLD_VERSION):
  x=CASES['e5_context']; old=source_version==e5.OLD_VERSION
  return E5MigrationDiagnosticsContext(x['old_schema_id'],x['old_version'],x['old_schema_fingerprint'],x['target_schema_id'],x['target_version'],x['target_schema_fingerprint'],x['old_schema_id'] if old else x['target_schema_id'],source_version,x['old_schema_fingerprint'] if old else x['target_schema_fingerprint'],e5.source_fingerprint(source),state)
 def test_exact_e4_schema_tuple(self):
  x=CASES['e4_schema']; self.assertEqual((self.ref.schema_id,self.ref.semantic_version,self.ref.content_fingerprint),(x['schema_id'],x['schema_version'],x['schema_fingerprint']))
 def test_representative_structural_diagnostics_are_e4_driven(self):
  source='app Demo {\n  mystery Core\n}\n'; start=source.index('mystery'); d=self.consumer.unknown_body_slot(source,start,start+7,self.current,'app','mystery'); self.assertIsInstance(d,StructuralDiagnostic); self.assertEqual(d.code,'AIDL-S003')
  source='entity Customer {\n  id: UUID magical\n}\n'; start=source.index('magical'); d=self.consumer.invalid_modifier(source,start,start+7,self.current,'entity','field','magical'); self.assertIsInstance(d,StructuralDiagnostic); self.assertEqual(d.code,'AIDL-S005')
  source='sync Mobile for Customer {\n  mode impossible\n}\n'; start=source.index('impossible'); d=self.consumer.wrong_closed_value(source,start,start+10,self.current,'sync-mode','impossible'); self.assertIsInstance(d,StructuralDiagnostic); self.assertEqual(d.code,'AIDL-S004')
 def test_known_structural_facts_produce_no_diagnostic(self):
  source='app Demo {\n  profile web version 1\n}\n'; start=source.index('profile'); self.assertIsNone(self.consumer.unknown_body_slot(source,start,start+7,self.current,'app','profile'))
  source='entity C {\n  id: UUID required\n}\n'; start=source.index('required'); self.assertIsNone(self.consumer.invalid_modifier(source,start,start+8,self.current,'entity','field','required'))
 def test_generic_vocabularies_are_exported_from_e4(self):
  for name,required in CASES['generic_vocabulary'].items():
   with self.subTest(name=name): self.assertTrue(set(required).issubset(self.consumer.sublanguage_vocabulary(self.current,name)))
 def test_unknown_generic_word_gets_schema_owned_structural_diagnostic(self):
  source='service S {\n  reliability { mystery Store }\n}\n'; start=source.index('mystery'); d=self.consumer.unknown_sublanguage_word(source,start,start+7,self.current,'profileProperty','mystery'); self.assertIsInstance(d,StructuralDiagnostic); self.assertEqual(d.code,'AIDL-S004'); self.assertIn('inboxStore',d.expected)
 def test_stale_or_unknown_metadata_fails_closed(self):
  stale=CurrentDiagnosticsContext(e4.SchemaRef(self.ref.schema_id,'0.1.0-e4','sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542'))
  with self.assertRaises(DiagnosticsContextError): self.consumer.unknown_body_slot('app A {}',0,3,stale,'app','x')
  with self.assertRaises(DiagnosticsContextError): self.consumer.sublanguage_vocabulary(self.current,'unknown')
 def test_locations_and_ordering_are_deterministic(self):
  source='app Demo {\n  first Bad\n  second Bad\n}\n'; a=source.index('first'); b=source.index('second'); da=self.consumer.unknown_body_slot(source,a,a+5,self.current,'app','first'); db=self.consumer.unknown_body_slot(source,b,b+6,self.current,'app','second'); ordered=self.consumer.order((db,da)); self.assertEqual([x.location.start for x in ordered],[a,b]); self.assertEqual(ordered[0].location.line,2)
 def test_structural_diagnostics_never_claim_compatibility_or_write_authority(self):
  source='sync M for C {\n  mode impossible\n}\n'; start=source.index('impossible'); d=self.consumer.wrong_closed_value(source,start,start+10,self.current,'sync-mode','impossible'); self.assertIsNone(d.compatibility_class); self.assertFalse(d.migration_authorized)
 def test_migration_state_is_explicit_legacy_coexistence_target(self):
  source=MIG['normalization_rows'][1]['old']; off=source.index('client')+1; self.assertIsNone(self.consumer.migration_diagnostic(source,off,self.migration_context(source,'legacy'))); dep=self.consumer.migration_diagnostic(source,off,self.migration_context(source,'coexistence')); inv=self.consumer.migration_diagnostic(source,off,self.migration_context(source,'target')); self.assertEqual(dep.code,'AIDL-S006'); self.assertEqual(inv.code,'AIDL-S007'); self.assertEqual(dep.replacement,inv.replacement); self.assertFalse(inv.migration_authorized)
 def test_target_snapshot_has_no_legacy_diagnostic(self):
  source=MIG['normalization_rows'][1]['candidate']; self.assertIsNone(self.consumer.migration_diagnostic(source,source.index('service:'),self.migration_context(source,'target',e5.TARGET_VERSION)))
 def test_migration_context_rejects_latest_old_candidate_v1_and_stale_fp(self):
  source=MIG['normalization_rows'][0]['old']; good=self.migration_context(source); bad=(dataclasses.replace(good,target_version='latest'),dataclasses.replace(good,target_version='m16.5-e5-candidate-v1'),dataclasses.replace(good,target_schema_fingerprint='sha256:'+'0'*64),dataclasses.replace(good,language_state='auto'))
  for c in bad:
   with self.assertRaises(DiagnosticsContextError): self.consumer.migration_diagnostic(source,source.index('projection')+1,c)
 def test_all_former_e5_shape_gaps_now_project_migration_diagnostics(self):
  ids={'explicit-index','queue-deadletter','schedule-lease','sync-outbox'}
  for row in [x for x in MIG['normalization_rows'] if x['id'] in ids]:
   with self.subTest(row=row['id']):
    plan=e5.plan_migration(row['old'],source_version=e5.OLD_VERSION,old_version=e5.OLD_VERSION,target_version=e5.TARGET_VERSION,source_schema_fingerprint=e5.OLD_SCHEMA_FINGERPRINT,target_schema_fingerprint=e5.TARGET_SCHEMA_FINGERPRINT,expected_source_fingerprint=e5.source_fingerprint(row['old'])); d=self.consumer.migration_diagnostic(row['old'],plan.edits[0].start+1,self.migration_context(row['old'])); self.assertIsInstance(d,StructuralDiagnostic); self.assertEqual(d.code,'AIDL-S007')
 def test_multi_source_projection_now_projects_without_fact_loss(self):
  source=MIG['multi_source_projection']['old']; d=self.consumer.migration_diagnostic(source,source.index('projection')+1,self.migration_context(source)); self.assertIsInstance(d,StructuralDiagnostic); self.assertEqual(d.code,'AIDL-S007'); self.assertIn('source: B',d.replacement)
 def test_semantic_intent_projection_requires_exact_e5_target(self):
  row=MIG['normalization_rows'][0]; intent=CompilerSemanticIntent('AIDL-T123','semantic','error','same compiler intent'); result=self.consumer.equivalent_semantic_intent(row['old'],row['candidate'],row['old'].index('projection')+1,self.migration_context(row['old']),intent); self.assertIsInstance(result,tuple); self.assertIsInstance(result[0],SemanticDiagnosticProjection); bad=self.consumer.equivalent_semantic_intent(row['old'],row['candidate']+'//changed\n',row['old'].index('projection')+1,self.migration_context(row['old']),intent); self.assertIsInstance(bad,DiagnosticUnavailable); self.assertEqual(bad.reason,'candidate-snapshot-mismatch')
 def test_source_contains_no_second_schema_or_production_diagnostics_import(self):
  source=pathlib.Path(e7.__file__).read_text(); self.assertIn('m16_5_e4_introspection',source); self.assertIn('m16_5_e5_migration',source); self.assertNotIn('ROW_IDS =',source); self.assertNotIn('RULES =',source); self.assertNotIn('aidl_parser',source); self.assertNotIn('AidlCompilerDiagnostics',source)
if __name__=='__main__': unittest.main()
