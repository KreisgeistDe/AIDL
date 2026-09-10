from __future__ import annotations
import json,pathlib,unittest
from dataclasses import replace
from tools.aidl_parser import parse_text
from tools.m16_5_e5_migration import *
ROOT=pathlib.Path(__file__).resolve().parents[1]; CASES=json.loads((ROOT/"fixtures/m16-5/e5-migration-cases.json").read_text())
def kwargs(s,source_version=OLD_VERSION): return dict(source_version=source_version,old_version=OLD_VERSION,target_version=TARGET_VERSION,source_schema_fingerprint=OLD_SCHEMA_FINGERPRINT if source_version==OLD_VERSION else TARGET_SCHEMA_FINGERPRINT,target_schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,expected_source_fingerprint=source_fingerprint(s))
class T(unittest.TestCase):
 def code(self,c,fn,*a,**k):
  with self.assertRaises(MigrationError) as e: fn(*a,**k)
  self.assertEqual(e.exception.diagnostic.code,c)
 def test_all_nine_rows_and_all_e3_replay(self):
  self.assertEqual([x['id'] for x in CASES['normalization_rows']],list(ROW_IDS))
  for x in CASES['normalization_rows']:
   r=migrate(x['old'],**kwargs(x['old'])); self.assertEqual(r.source,x['candidate']); self.assertEqual(set(r.plan.e3_replayed_rows),{x['id']}); self.assertEqual(r.plan.old_facts,r.plan.target_facts)
 def test_multi_source_projection_is_lossless_and_replayed(self):
  x=CASES['multi_source_projection']; r=migrate(x['old'],**kwargs(x['old'])); self.assertEqual(r.source,x['candidate']); self.assertEqual(r.plan.old_facts,r.plan.target_facts); self.assertIn('projection-relationship',r.plan.e3_replayed_rows); self.assertEqual(dict(r.plan.target_facts[0].facts)['sources'],('A','B'))
 def test_old_validation_preserves_bounded_schedule_parser_gap(self):
  for x in CASES['normalization_rows']:
   _,ds,_=parse_text(x['old']); p=plan_migration(x['old'],**kwargs(x['old']))
   if x['id']=='schedule-lease': self.assertTrue(ds); self.assertEqual({d.message for d in ds},{'expected declaration'})
   else:self.assertEqual(ds,[])
   self.assertEqual(set(p.e3_replayed_rows),{x['id']})
 def test_explicit_target_noop(self):
  for x in CASES['normalization_rows']+[CASES['multi_source_projection']]:
   first=migrate(x['old'],**kwargs(x['old'])); p=plan_migration(first.source,**kwargs(first.source,TARGET_VERSION)); self.assertEqual(p.edits,())
 def test_deterministic_apply_and_rollback(self):
  x=CASES['normalization_rows'][0]; p1=plan_migration(x['old'],**kwargs(x['old']));p2=plan_migration(x['old'],**kwargs(x['old']));self.assertEqual(p1,p2);self.assertEqual(apply_plan(x['old'],p1).source,x['candidate']);self.assertEqual(p1.rollback_source,x['old'])
 def test_comments_and_modifiers_preserved(self):
  s="entity Customer {\n  @pii\n  email: String required unique // preserve me\n}\n";r=migrate(s,**kwargs(s));self.assertIn("field email: String required unique // preserve me",r.source);self.assertEqual(dict(r.plan.target_facts[0].facts)['modifiers'],('required','unique'))
 def test_stale_fingerprints_fail_closed(self):
  s=CASES['normalization_rows'][1]['old'];k=kwargs(s);k['expected_source_fingerprint']='sha256:stale';self.code('AIDL-S008',plan_migration,s,**k)
 def test_anchor_failures_closed(self):
  s=CASES['normalization_rows'][3]['old'];side=build_sidecar(s,source_version=OLD_VERSION,schema_fingerprint=OLD_SCHEMA_FINGERPRINT);self.code('AIDL-S005',plan_migration,s,sidecar=with_anchors(side,()),**kwargs(s));dup=with_anchors(side,(*side.anchors,side.anchors[0]));self.code('AIDL-S005',plan_migration,s,sidecar=dup,**kwargs(s))
 def test_formatter_same_version_only(self):
  x=CASES['normalization_rows'][6];messy=x['candidate'].replace('deadLetter: 5 attempts','deadLetter :   5   attempts');self.assertEqual(format_candidate(messy,source_version=TARGET_VERSION,schema_fingerprint=TARGET_SCHEMA_FINGERPRINT),x['candidate']);self.code('AIDL-S007',format_candidate,x['old'],source_version=TARGET_VERSION,schema_fingerprint=TARGET_SCHEMA_FINGERPRINT)
 def test_unchanged_order_preserved(self):
  for x in CASES['unchanged']:
   p=plan_migration(x['source'],**kwargs(x['source']));self.assertEqual(p.edits,());self.assertEqual(apply_plan(x['source'],p).source,x['source'])
 def test_old_fingerprint_stays_v1_target_identity_is_new(self):
  self.assertEqual(OLD_SCHEMA_FINGERPRINT,'sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822');self.assertEqual(TARGET_VERSION,'m16.5-e5-candidate-v2');self.assertNotEqual(TARGET_SCHEMA_FINGERPRINT,'sha256:c702262d2f5374d8eda54a028923d00d7d21e45d3980c62f32d472392ccc8c30')
 def test_old_target_v1_tuple_is_stale_for_changed_candidate_schema(self):
  source=CASES['normalization_rows'][0]['candidate']
  self.code('AIDL-S008',plan_migration,source,source_version='m16.5-e5-candidate-v1',old_version=OLD_VERSION,target_version=TARGET_VERSION,source_schema_fingerprint='sha256:c702262d2f5374d8eda54a028923d00d7d21e45d3980c62f32d472392ccc8c30',target_schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,expected_source_fingerprint=source_fingerprint(source))
if __name__=='__main__':unittest.main()
