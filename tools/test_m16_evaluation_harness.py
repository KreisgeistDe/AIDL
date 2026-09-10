from __future__ import annotations
import copy, dataclasses, hashlib, json, pathlib, tempfile, types, unittest
from unittest.mock import patch
from tools import m16_evaluation_harness as h
from tools import m16_5_e3_prototype as e3
from tools import m16_5_e4_introspection as e4
from tools import m16_5_e5_migration as e5
from tools.m16_5_e6_completion import CompletionUnavailable, ExperimentalCompletionConsumer
from tools.m16_5_e7_diagnostics import DiagnosticUnavailable, ExperimentalDiagnosticsConsumer
ROOT=pathlib.Path(__file__).resolve().parents[1]

def corpus_task(i,surfaces,facts):
 return {'id':f'm16-{i:03d}','mode':'construct','family':'Synthetic','requirement':f'Construct semantic requirement {i}.','initialProject':{'kind':'emptyModule','value':f'eval.synthetic.t{i}'},'expectedSemanticFacts':facts,'requiredSurfaces':surfaces,'tags':[]}
def synthetic_corpus():
 tasks=[
  corpus_task(1,['multi-source-projection'],['projection:P','source:P=A','source:P=B','target:P=V']),
  corpus_task(2,['index-direction'],['index:E.i','indexField:E.i[0]=a:desc']),
  corpus_task(3,['dead-letter-threshold'],['topic:T','deadLetterAttempts:T=8']),
  corpus_task(4,['schedule-lease'],['schedule:S','task:S=T','singleton:S=true','lease:S=30s']),
  corpus_task(5,['sync-outbox'],['sync:S','changesTarget:S=E','changesDelivery:S=outbox']),
  corpus_task(6,['profileProperty'],['reliability:S.inboxStore=Db']),
  corpus_task(7,['uiStatement'],['ui:Page.heading=status']),
  corpus_task(8,['testStatement'],['testCall:t=getPet','testAssert:t=resultPresent']),
  corpus_task(9,['value','field'],['value:V','field:V.x','type:V.x=string','optional:V.x']),
 ]
 tasks.extend(corpus_task(i,['entity'],[f'entity:E{i}']) for i in range(10,51))
 c={'schemaVersion':1,'corpusId':'urn:aidl:evaluation:synthetic-readiness-v1','projectBase':h.PROJECT_BASE,'purpose':'Synthetic deterministic readiness unit contract.','taskCount':50,'taskIdPolicy':'stable synthetic sequence','surfaceNeutrality':'semantic only','tasks':tasks}
 c['fingerprint']=h._canonical_fingerprint(c); h.validate_corpus(c); return c
def synthetic_baseline(c):
 b={'schemaVersion':1,'baselineId':'urn:aidl:evaluation:synthetic-before-v1','projectBase':h.PROJECT_BASE,'surface':'current','corpusId':c['corpusId'],'corpusFingerprint':c['fingerprint'],'surfaceAuthority':{'commit':h.PROJECT_BASE,'candidateSyntaxAuthorized':False},'executionContract':{'contextBudgetTokens':32000,'retryLimit':2,'seedPolicy':{'kind':'fixed-when-supported','seed':42},'acceptanceChecks':['aidl check <task-worktree> --format json','aidl ir <task-worktree> --format json']}}
 b['fingerprint']=h._canonical_fingerprint(b); return b
def git_blob_sha(path):
 data=path.read_bytes(); return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
class BadCompletion:
 def sublanguage_vocabulary(self,*a,**k): return CompletionUnavailable('missing','missing','test')
class BadDiagnostics:
 def sublanguage_vocabulary(self,*a,**k): return DiagnosticUnavailable('missing','missing','test')
class HarnessTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.synthetic=synthetic_corpus(); cls.baseline=synthetic_baseline(cls.synthetic)
 def status(self,*,e3c=None,e4c=None,rows=None,e6=None,e7=None):
  return h._candidate_readiness_from(self.synthetic,e3c or e3.build_catalog(),e4c or e4.build_catalog(),set(e5.FACT_COMPLETE_ROW_IDS) if rows is None else set(rows),e6 or ExperimentalCompletionConsumer(),e7 or ExperimentalDiagnosticsConsumer())
 def test_synthetic_all_covered_status_is_derived_true(self):
  s=self.status(); self.assertTrue(s['ready'],s); self.assertEqual(s['unavailableTaskCount'],0); self.assertTrue(all(s['coverage']['genericVocabulary'].values()))
 def test_each_former_fact_gap_turns_readiness_false_when_its_mapping_is_removed(self):
  mapping={'projection-relationship':'m16-001','explicit-index':'m16-002','queue-deadletter':'m16-003','schedule-lease':'m16-004','sync-outbox':'m16-005'}
  for row,task in mapping.items():
   with self.subTest(row=row):
    s=self.status(rows=set(e5.FACT_COMPLETE_ROW_IDS)-{row}); self.assertFalse(s['ready']); self.assertIn(task,s['unavailableTasks'])
 def test_missing_profile_ui_or_test_vocabulary_turns_readiness_false(self):
  c=e4.build_catalog()
  for name,task in [('profileProperty','m16-006'),('uiStatement','m16-007'),('testStatement','m16-008')]:
   with self.subTest(name=name):
    subs=tuple(dataclasses.replace(x,vocabulary=()) if x.name==name else x for x in c.sublanguages); broken=dataclasses.replace(c,sublanguages=subs); s=self.status(e4c=broken); self.assertFalse(s['ready']); self.assertIn(task,s['unavailableTasks'])
 def test_consumer_vocabulary_mismatch_turns_readiness_false(self):
  s=self.status(e6=BadCompletion()); self.assertFalse(s['ready']); self.assertTrue({'m16-006','m16-007','m16-008'}.issubset(s['unavailableTasks']))
  s=self.status(e7=BadDiagnostics()); self.assertFalse(s['ready']); self.assertTrue({'m16-006','m16-007','m16-008'}.issubset(s['unavailableTasks']))
 def test_missing_construction_surface_turns_readiness_false(self):
  c=e4.build_catalog(); broken=dataclasses.replace(c,construction_surfaces=tuple(x for x in c.construction_surfaces if x.surface_id!='value')); s=self.status(e4c=broken); self.assertFalse(s['ready']); self.assertIn('m16-009',s['unavailableTasks'])
 def test_missing_semantic_fact_projection_turns_readiness_false(self):
  c=e4.build_catalog(); surfaces=tuple(dataclasses.replace(x,semantic_fact_prefixes=()) if x.surface_id=='value' else x for x in c.construction_surfaces); s=self.status(e4c=dataclasses.replace(c,construction_surfaces=surfaces)); self.assertFalse(s['ready']); self.assertTrue(any(x['kind']=='missing-semantic-fact' for x in s['unavailableTasks']['m16-009']))
 def test_stale_e4_identity_fails_closed_not_false_positive(self):
  c=e4.build_catalog(); stale=dataclasses.replace(c,schema_ref=e4.SchemaRef(c.schema_ref.schema_id,'0.1.0-e4','sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542'))
  with patch.object(e4,'build_catalog',return_value=stale):
   with self.assertRaisesRegex(h.EvaluationContractError,'E4 exact schema tuple'): h.prototype_candidate_status(self.synthetic)
 def test_stale_e3_identity_fails_closed(self):
  c=e3.build_catalog(); stale=dataclasses.replace(c,version='m16.5-e3-candidate-v1')
  with patch.object(e3,'build_catalog',return_value=stale):
   with self.assertRaisesRegex(h.EvaluationContractError,'E3 exact schema tuple'): h.prototype_candidate_status(self.synthetic)
 def test_frozen_inputs_and_current_runner_remain_exact_when_full_repo_present(self):
  corpus=ROOT/'fixtures/m16-5/m16-agent-task-corpus.json'; base=ROOT/'fixtures/m16-5/m16-before-baseline.json'; runner=ROOT/'tools/m16_evaluation_runner.py'
  if not (corpus.exists() and base.exists() and runner.exists()): self.skipTest('isolated recovery workspace lacks frozen/full-repo files')
  self.assertEqual(git_blob_sha(corpus),'c8dae3b9babf0c89bcd942a7d0c94a70dc537f82'); self.assertEqual(git_blob_sha(base),'5ee06d6537ce5457c73bbf571fb72ca17188a2c5'); self.assertEqual(git_blob_sha(runner),'692e3cf1c36c98952786472828934f62a46f30d5')
  c=json.loads(corpus.read_text()); b=json.loads(base.read_text()); self.assertEqual(c['fingerprint'],'sha256:e47b399c2460f576a2f68023af039412f02395de67f8204f3785bf9d7d8dfcef'); self.assertEqual(b['fingerprint'],'sha256:d5c7e9cd2003cfa970707e11d8cb130c80aac056028630aa3b7679e2790b7110')
 def test_full_frozen_corpus_readiness_is_true_when_full_repo_present(self):
  path=ROOT/'fixtures/m16-5/m16-agent-task-corpus.json'
  if not path.exists(): self.skipTest('isolated recovery workspace lacks frozen corpus')
  c=h.load_corpus(ROOT); s=h.prototype_candidate_status(c); self.assertTrue(s['ready'],json.dumps(s,indent=2,sort_keys=True)); self.assertEqual(s['unavailableTaskCount'],0)
 def test_frozen_corpus_fingerprint_and_neutral_wording_when_present(self):
  path=ROOT/'fixtures/m16-5/m16-agent-task-corpus.json'
  if not path.exists(): self.skipTest('isolated recovery workspace lacks frozen corpus')
  c=h.load_corpus(ROOT); h.validate_corpus(c); self.assertEqual(c['fingerprint'],'sha256:e47b399c2460f576a2f68023af039412f02395de67f8204f3785bf9d7d8dfcef'); self.assertEqual([x['id'] for x in c['tasks']],[f'm16-{i:03d}' for i in range(1,51)])
 def test_corpus_tamper_fails_closed(self):
  c=copy.deepcopy(self.synthetic); c['tasks'][0]['requirement']+=' changed'
  with self.assertRaisesRegex(h.EvaluationContractError,'fingerprint'): h.validate_corpus(c)
 def test_baseline_contract_is_exact_and_valid(self):
  with tempfile.TemporaryDirectory() as td: h.validate_baseline(self.baseline,self.synthetic,root=pathlib.Path(td))
  self.assertFalse(self.baseline['surfaceAuthority']['candidateSyntaxAuthorized']); self.assertEqual(self.baseline['executionContract']['retryLimit'],2)
 def all_success_record(self,surface='current'):
  tasks=[]
  for t in self.synthetic['tasks']:
   a={'parseSuccess':True,'semanticValidationSuccess':True,'compileSuccess':True,'observedSemanticFacts':list(t['expectedSemanticFacts']),'falseAssumptions':[],'invalidCombinations':[],'errors':[],'inventedSyntax':[],'wrongPlacement':[],'diagnostics':[],'sourceLines':20,'regressions':0,'tokenCost':{'available':True,'inputTokens':100,'outputTokens':40,'totalTokens':140,'unavailableReason':None},'patch':{'filesTouched':1,'linesAdded':4,'linesDeleted':1,'unnecessaryEdits':0},'humanRewrite':'none'}
   tasks.append({'taskId':t['id'],'attempts':[a]})
  r={'schemaVersion':1,'runId':f'test-{surface}','surface':surface,'corpusId':self.synthetic['corpusId'],'corpusFingerprint':self.synthetic['fingerprint'],'baselineId':self.baseline['baselineId'],'baselineFingerprint':self.baseline['fingerprint'],'executionContract':copy.deepcopy(self.baseline['executionContract']),'tasks':tasks}; return h.fingerprint_run_record(r)
 def test_all_success_run_aggregates_deterministically(self):
  r=self.all_success_record(); a=h.summarize_run(r,self.synthetic,self.baseline); b=h.summarize_run(r,self.synthetic,self.baseline); self.assertEqual(a,b); self.assertEqual(a['raw']['outputCorrectTasks'],50); self.assertEqual(a['rates']['semanticFactRecall'],1.0); self.assertEqual(a['tokenCost']['totalTokens'],7000)
 def test_missing_fact_and_failures_are_not_normalized_away(self):
  r=self.all_success_record(); r.pop('fingerprint'); a=r['tasks'][0]['attempts'][0]; a['observedSemanticFacts'].pop(); a['falseAssumptions']=['bad']; a['invalidCombinations']=['bad']; a['errors']=['bad']; a['regressions']=1; r=h.fingerprint_run_record(r); s=h.summarize_run(r,self.synthetic,self.baseline); self.assertEqual(s['raw']['outputCorrectTasks'],49); self.assertEqual(s['raw']['missingFacts'],1); self.assertEqual(s['raw']['regressions'],1)
 def test_retry_limit_and_contract_mismatch_fail_closed(self):
  r=self.all_success_record(); r.pop('fingerprint'); a=r['tasks'][0]['attempts'][0]; r['tasks'][0]['attempts']=[copy.deepcopy(a) for _ in range(4)]; r=h.fingerprint_run_record(r)
  with self.assertRaisesRegex(h.EvaluationContractError,'retry limit'): h.validate_run_record(r,self.synthetic,self.baseline)
  r=self.all_success_record(); r.pop('fingerprint'); r['executionContract']['contextBudgetTokens']+=1; r=h.fingerprint_run_record(r)
  with self.assertRaisesRegex(h.EvaluationContractError,'executionContract'): h.validate_run_record(r,self.synthetic,self.baseline)
 def test_unavailable_token_cost_is_counted(self):
  r=self.all_success_record(); r.pop('fingerprint'); c=r['tasks'][0]['attempts'][0]['tokenCost']; c.update({'available':False,'inputTokens':None,'outputTokens':None,'totalTokens':None,'unavailableReason':'not exposed'}); r=h.fingerprint_run_record(r); s=h.summarize_run(r,self.synthetic,self.baseline); self.assertEqual(s['tokenCost']['unavailableTasks'],1)
 def test_compare_is_permitted_only_when_derived_readiness_is_true(self):
  before=self.all_success_record('current'); candidate=self.all_success_record('candidate')
  with patch.object(h,'prototype_candidate_status',return_value={'ready':True}): result=h.compare_runs(before,candidate,self.synthetic,self.baseline)
  self.assertEqual(result['rateDeltaCandidateMinusBefore']['outputCorrectness'],0.0)
  with patch.object(h,'prototype_candidate_status',return_value={'ready':False}):
   with self.assertRaisesRegex(h.EvaluationContractError,'candidate comparison unavailable'): h.compare_runs(before,candidate,self.synthetic,self.baseline)
 def test_human_rewrite_is_machine_counted(self):
  r=self.all_success_record(); r.pop('fingerprint'); r['tasks'][0]['attempts'][0]['humanRewrite']='minor'; r['tasks'][1]['attempts'][0]['humanRewrite']='substantial'; r=h.fingerprint_run_record(r); s=h.summarize_run(r,self.synthetic,self.baseline); self.assertEqual(s['humanRewrite']['minor'],1); self.assertEqual(s['humanRewrite']['substantial'],1)
if __name__=='__main__': unittest.main()
