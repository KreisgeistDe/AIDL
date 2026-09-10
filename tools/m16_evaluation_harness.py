"""M16 bounded vendor-neutral evaluation prerequisite and deterministic readiness gate."""
from __future__ import annotations
import argparse,copy,hashlib,json
from collections import Counter
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
CORPUS_PATH=Path('fixtures/m16-5/m16-agent-task-corpus.json');BASELINE_PATH=Path('fixtures/m16-5/m16-before-baseline.json')
PROJECT_BASE='a5c359b501913f7adce92792dec244add0452909'
E3_SCHEMA_ID='urn:aidl:schema:language:m16.5-e3-candidate';E3_SCHEMA_VERSION='m16.5-e3-candidate-v2';E3_SCHEMA_FINGERPRINT='sha256:367b920826a5c85ced83e58ddaec959e8539064e4f04e49486655c54bf695d85'
E4_SCHEMA_ID='urn:aidl:schema:meta:m16.5-e4-introspection';E4_SCHEMA_VERSION='0.2.0-e4';E4_SCHEMA_FINGERPRINT='sha256:68465a548d3322af3ae2d14df018fde1f08cdd161ce864f648f96a32a20dfdf2'
E5_OLD_SCHEMA_ID='urn:aidl:schema:language:m16.5-e5-current';E5_OLD_VERSION='m16.5-e5-current-v1';E5_OLD_FINGERPRINT='sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822'
E5_TARGET_SCHEMA_ID='urn:aidl:schema:language:m16.5-e5-candidate';E5_TARGET_VERSION='m16.5-e5-candidate-v2';E5_TARGET_FINGERPRINT='sha256:b30abd7f3534e7792c041ecf1e67f22c264be05712324a36096056dde5cebaf5'
HUMAN_REWRITE=('none','minor','substantial','rejected','not-reviewed')
CANDIDATE_NEUTRALITY_PATTERNS=('source:','target:','service:','deadLetter:','singleton:','changes:')
class EvaluationContractError(ValueError):pass
def _load(path):
 v=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(v,dict):raise EvaluationContractError(f'{path}: expected a JSON object')
 return v
def _canonical_fingerprint(value):
 u=dict(value);u.pop('fingerprint',None);p=json.dumps(u,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();return 'sha256:'+hashlib.sha256(p).hexdigest()
def _require(c,m):
 if not c:raise EvaluationContractError(m)
def _non_negative_int(v,p):_require(isinstance(v,int) and not isinstance(v,bool) and v>=0,f'{p}: expected non-negative integer');return v
def _ratio(n,d):return 0.0 if d==0 else n/d
def load_corpus(root=ROOT):return _load(root/CORPUS_PATH)
def load_baseline(root=ROOT):return _load(root/BASELINE_PATH)
def validate_corpus(corpus):
 _require(corpus.get('schemaVersion')==1,'corpus.schemaVersion must be 1');_require(corpus.get('projectBase')==PROJECT_BASE,'corpus projectBase mismatch');_require(corpus.get('taskCount')==50,'corpus must freeze exactly 50 tasks');tasks=corpus.get('tasks');_require(isinstance(tasks,list) and len(tasks)==50,'corpus.tasks must contain 50 tasks');_require([x.get('id') for x in tasks]==[f'm16-{i:03d}' for i in range(1,51)],'corpus task IDs/order must be the frozen m16-001..m16-050 sequence')
 for i,t in enumerate(tasks):
  p=f'corpus.tasks[{i}]';_require(t.get('mode') in {'construct','change'},f'{p}.mode invalid');_require(isinstance(t.get('family'),str) and t['family'],f'{p}.family required');r=t.get('requirement');_require(isinstance(r,str) and r.strip(),f'{p}.requirement required')
  for marker in CANDIDATE_NEUTRALITY_PATTERNS:_require(marker.lower() not in r.lower(),f'{p}.requirement teaches candidate spelling {marker!r}')
  initial=t.get('initialProject');_require(isinstance(initial,dict) and initial.get('kind') in {'repoPath','emptyModule'} and isinstance(initial.get('value'),str) and initial['value'],f'{p}.initialProject invalid')
  facts=t.get('expectedSemanticFacts');_require(isinstance(facts,list) and facts and all(isinstance(x,str) and x for x in facts) and len(facts)==len(set(facts)),f'{p}.expectedSemanticFacts invalid')
  surfaces=t.get('requiredSurfaces');_require(isinstance(surfaces,list) and surfaces and all(isinstance(x,str) and x for x in surfaces),f'{p}.requiredSurfaces required')
 _require(corpus.get('fingerprint')==_canonical_fingerprint(corpus),'corpus fingerprint mismatch')
def validate_baseline(baseline,corpus,*,root=ROOT):
 _require(baseline.get('schemaVersion')==1,'baseline.schemaVersion must be 1');_require(baseline.get('projectBase')==PROJECT_BASE,'baseline projectBase mismatch');_require(baseline.get('surface')=='current','baseline surface must be current');_require(baseline.get('corpusId')==corpus['corpusId'],'baseline corpusId mismatch');_require(baseline.get('corpusFingerprint')==corpus['fingerprint'],'baseline corpus fingerprint mismatch');a=baseline.get('surfaceAuthority');_require(isinstance(a,dict) and a.get('commit')==PROJECT_BASE,'baseline authority commit mismatch');_require(a.get('candidateSyntaxAuthorized') is False,'baseline must not authorize candidate syntax');c=baseline.get('executionContract');_require(isinstance(c,dict),'baseline.executionContract required');_non_negative_int(c.get('contextBudgetTokens'),'baseline.executionContract.contextBudgetTokens');_non_negative_int(c.get('retryLimit'),'baseline.executionContract.retryLimit');seed=c.get('seedPolicy');_require(isinstance(seed,dict) and seed.get('kind')=='fixed-when-supported','baseline seed policy must be explicit fixed-when-supported');_non_negative_int(seed.get('seed'),'baseline.executionContract.seedPolicy.seed');_require(c.get('acceptanceChecks')==['aidl check <task-worktree> --format json','aidl ir <task-worktree> --format json'],'baseline acceptance checks changed')
 for t in corpus['tasks']:
  initial=t['initialProject']
  if initial['kind']=='repoPath':_require((root/initial['value']).exists(),f"{t['id']}: pinned repoPath missing: {initial['value']}")
 _require(baseline.get('fingerprint')==_canonical_fingerprint(baseline),'baseline fingerprint mismatch')
def validate_frozen_prerequisite(root=ROOT):
 c=load_corpus(root);b=load_baseline(root);validate_corpus(c);validate_baseline(b,c,root=root);return c,b
def _prefix(fact):return fact.split(':',1)[0]
def _candidate_readiness_from(corpus,e3_catalog,e4_catalog,e5_fact_complete_rows,e6_consumer,e7_consumer):
 validate_corpus(corpus)
 unavailable={};surface_map={}
 for s in e4_catalog.construction_surfaces:
  surface_map.setdefault(s.surface_id,[]).append(('E4',set(s.semantic_fact_prefixes),s.fact_complete))
 for shape in e3_catalog.enabled_shapes():
  complete=shape.normalization_row in e5_fact_complete_rows if shape.normalization_row else True
  for sid in shape.semantic_surfaces:
   surface_map.setdefault(sid,[]).append(('E3',set(shape.semantic_fact_prefixes),complete))
 # Closed generic sublanguages own their fact projection and vocabulary in E4.
 # E6 and E7 must independently consume the exact same exported vocabulary.
 from tools.m16_5_e6_completion import CompletionSet,CurrentCompletionContext
 from tools.m16_5_e7_diagnostics import CurrentDiagnosticsContext,DiagnosticUnavailable
 generic_ok={}
 for schema in e4_catalog.sublanguages:
  if not schema.semantic_fact_prefixes:
   continue
  ok=bool(schema.closed_vocabulary and schema.vocabulary)
  if ok:
   try:
    c=e6_consumer.sublanguage_vocabulary(CurrentCompletionContext(e4_catalog.schema_ref),schema.name)
    d=e7_consumer.sublanguage_vocabulary(CurrentDiagnosticsContext(e4_catalog.schema_ref),schema.name)
    ok=(
      isinstance(c,CompletionSet) and bool(c.items) and not isinstance(d,DiagnosticUnavailable)
      and tuple(x.insert_text for x in c.items)==tuple(d)==schema.vocabulary
    )
   except Exception:
    ok=False
  generic_ok[schema.name]=ok
  surface_map.setdefault(schema.name,[]).append(('E4-sublanguage',set(schema.semantic_fact_prefixes),ok))
 for t in corpus['tasks']:
  reasons=[];covered=set()
  for sid in t['requiredSurfaces']:
   providers=surface_map.get(sid,[])
   if not providers:
    reasons.append({'kind':'missing-surface','surface':sid});continue
   complete=[provider for provider in providers if provider[2]]
   if not complete:
    reasons.append({'kind':'incomplete-surface','surface':sid});continue
   for _,facts,_ in complete:covered.update(facts)
  for fact in t['expectedSemanticFacts']:
   prefix=_prefix(fact)
   if prefix not in covered:
    reasons.append({'kind':'missing-semantic-fact','fact':fact,'prefix':prefix})
  if reasons:unavailable[t['id']]=reasons
 blockers=[]
 if unavailable:blockers.append('prototype/compiler-owned coverage is incomplete for one or more frozen tasks')
 return {
  'ready':not unavailable,
  'unavailableTaskCount':len(unavailable),
  'unavailableTasks':unavailable,
  'blockers':blockers,
  'coverage':{'surfaceCount':len(surface_map),'genericVocabulary':generic_ok},
 }
def prototype_candidate_status(corpus=None):
 if corpus is None:corpus=load_corpus();validate_corpus(corpus)
 from tools import m16_5_e3_prototype as e3,m16_5_e4_introspection as e4,m16_5_e5_migration as e5
 from tools.m16_5_e6_completion import ExperimentalCompletionConsumer
 from tools.m16_5_e7_diagnostics import ExperimentalDiagnosticsConsumer
 e3c=e3.build_catalog();e4c=e4.build_catalog()
 _require((e3c.schema_id,e3c.version,e3c.fingerprint)==(E3_SCHEMA_ID,E3_SCHEMA_VERSION,E3_SCHEMA_FINGERPRINT),'integrated E3 exact schema tuple differs from frozen evaluation prerequisite')
 ref=e4c.schema_ref;_require((ref.schema_id,ref.semantic_version,ref.content_fingerprint)==(E4_SCHEMA_ID,E4_SCHEMA_VERSION,E4_SCHEMA_FINGERPRINT),'integrated E4 exact schema tuple differs from frozen evaluation prerequisite')
 _require((e5.OLD_SCHEMA_ID,e5.OLD_VERSION,e5.OLD_SCHEMA_FINGERPRINT)==(E5_OLD_SCHEMA_ID,E5_OLD_VERSION,E5_OLD_FINGERPRINT),'integrated E5 old context differs from frozen evaluation prerequisite');_require((e5.TARGET_SCHEMA_ID,e5.TARGET_VERSION,e5.TARGET_SCHEMA_FINGERPRINT)==(E5_TARGET_SCHEMA_ID,E5_TARGET_VERSION,E5_TARGET_FINGERPRINT),'integrated E5 target context differs from frozen evaluation prerequisite')
 out=_candidate_readiness_from(corpus,e3c,e4c,set(e5.FACT_COMPLETE_ROW_IDS),ExperimentalCompletionConsumer(),ExperimentalDiagnosticsConsumer());out.update({'e3Schema':{'id':e3c.schema_id,'version':e3c.version,'fingerprint':e3c.fingerprint},'e4Schema':{'id':ref.schema_id,'version':ref.semantic_version,'fingerprint':ref.content_fingerprint},'e5Old':{'id':e5.OLD_SCHEMA_ID,'version':e5.OLD_VERSION,'fingerprint':e5.OLD_SCHEMA_FINGERPRINT},'e5Target':{'id':e5.TARGET_SCHEMA_ID,'version':e5.TARGET_VERSION,'fingerprint':e5.TARGET_SCHEMA_FINGERPRINT}});return out
def _validate_token_cost(v,p):
 _require(isinstance(v,dict),f'{p}: tokenCost must be object');a=v.get('available');_require(isinstance(a,bool),f'{p}.available must be boolean')
 if a:i=_non_negative_int(v.get('inputTokens'),f'{p}.inputTokens');o=_non_negative_int(v.get('outputTokens'),f'{p}.outputTokens');_require(v.get('totalTokens')==i+o,f'{p}.totalTokens must equal inputTokens + outputTokens');_require(v.get('unavailableReason') is None,f'{p}.unavailableReason must be null')
 else:_require(v.get('inputTokens') is None and v.get('outputTokens') is None and v.get('totalTokens') is None,f'{p}: unavailable token cost must use null numeric values');_require(isinstance(v.get('unavailableReason'),str) and v['unavailableReason'].strip(),f'{p}.unavailableReason required when unavailable')
def _validate_attempt(a,p):
 _require(isinstance(a,dict),f'{p}: attempt must be object')
 for n in ('parseSuccess','semanticValidationSuccess','compileSuccess'):_require(isinstance(a.get(n),bool),f'{p}.{n} must be boolean')
 for n in ('observedSemanticFacts','falseAssumptions','invalidCombinations','errors','inventedSyntax','wrongPlacement','diagnostics'):_require(isinstance(a.get(n),list) and all(isinstance(x,str) for x in a[n]),f'{p}.{n} must be string array')
 _validate_token_cost(a.get('tokenCost'),f'{p}.tokenCost');patch=a.get('patch');_require(isinstance(patch,dict),f'{p}.patch must be object')
 for n in ('filesTouched','linesAdded','linesDeleted','unnecessaryEdits'):_non_negative_int(patch.get(n),f'{p}.patch.{n}')
 _non_negative_int(a.get('sourceLines'),f'{p}.sourceLines');_non_negative_int(a.get('regressions'),f'{p}.regressions');_require(a.get('humanRewrite') in HUMAN_REWRITE,f'{p}.humanRewrite invalid')
def validate_run_record(record,corpus,baseline):
 _require(record.get('schemaVersion')==1,'run.schemaVersion must be 1');_require(isinstance(record.get('runId'),str) and record['runId'],'run.runId required');_require(record.get('surface') in {'current','candidate'},'run.surface invalid');_require(record.get('corpusId')==corpus['corpusId'],'run corpusId mismatch');_require(record.get('corpusFingerprint')==corpus['fingerprint'],'run corpus fingerprint mismatch');_require(record.get('baselineId')==baseline['baselineId'],'run baselineId mismatch');_require(record.get('baselineFingerprint')==baseline['fingerprint'],'run baseline fingerprint mismatch');_require(record.get('executionContract')==baseline['executionContract'],'run executionContract must byte-semantically equal frozen before contract');entries=record.get('tasks');_require(isinstance(entries,list) and len(entries)==len(corpus['tasks']),'run.tasks must contain one result for every frozen task');_require([x.get('taskId') for x in entries]==[x['id'] for x in corpus['tasks']],'run task IDs/order must equal frozen corpus');limit=baseline['executionContract']['retryLimit']
 for i,e in enumerate(entries):
  p=f'run.tasks[{i}]';_require(isinstance(e,dict),f'{p} must be object');attempts=e.get('attempts');_require(isinstance(attempts,list) and attempts,f'{p}.attempts must be non-empty');_require(len(attempts)<=limit+1,f'{p}.attempts exceeds frozen retry limit')
  for j,a in enumerate(attempts):_validate_attempt(a,f'{p}.attempts[{j}]')
 _require(record.get('fingerprint')==_canonical_fingerprint(record),'run fingerprint mismatch')
def _task_correct(task,a):
 observed=set(a['observedSemanticFacts']);expected=set(task['expectedSemanticFacts']);missing=sorted(expected-observed);correct=a['parseSuccess'] and a['semanticValidationSuccess'] and a['compileSuccess'] and not missing and not a['falseAssumptions'] and not a['invalidCombinations'] and not a['errors'] and a['regressions']==0;return correct,missing
def summarize_run(record,corpus=None,baseline=None):
 if corpus is None or baseline is None:corpus,baseline=validate_frozen_prerequisite()
 validate_run_record(record,corpus,baseline);total=len(corpus['tasks']);by={x['id']:x for x in corpus['tasks']};names=['output_correct','first_pass','first_parse','first_semantic','first_compile','missing','false','invalid','retries','errors','invented','wrong','regressions','diagnostics','source_lines','files','added','deleted','unnecessary','input','output','tok_avail','tok_unavail'];v={x:0 for x in names};rewrite=Counter();raw=[]
 for e in record['tasks']:
  t=by[e['taskId']];ats=e['attempts'];first=ats[0];final=ats[-1];fc,_=_task_correct(t,first);ok,missing=_task_correct(t,final);v['first_pass']+=int(fc);v['output_correct']+=int(ok);v['first_parse']+=int(first['parseSuccess']);v['first_semantic']+=int(first['semanticValidationSuccess']);v['first_compile']+=int(first['compileSuccess']);v['retries']+=len(ats)-1;v['missing']+=len(missing);v['false']+=len(final['falseAssumptions']);v['invalid']+=len(final['invalidCombinations']);v['errors']+=len(final['errors']);v['invented']+=len(final['inventedSyntax']);v['wrong']+=len(final['wrongPlacement']);v['regressions']+=final['regressions'];v['diagnostics']+=len(final['diagnostics']);v['source_lines']+=final['sourceLines'];p=final['patch'];v['files']+=p['filesTouched'];v['added']+=p['linesAdded'];v['deleted']+=p['linesDeleted'];v['unnecessary']+=p['unnecessaryEdits'];rewrite[final['humanRewrite']]+=1;c=final['tokenCost']
  if c['available']:v['tok_avail']+=1;v['input']+=c['inputTokens'];v['output']+=c['outputTokens']
  else:v['tok_unavail']+=1
  if not ok:raw.append({'taskId':e['taskId'],'missingFacts':missing,'falseAssumptions':list(final['falseAssumptions']),'invalidCombinations':list(final['invalidCombinations']),'errors':list(final['errors']),'regressions':final['regressions']})
 facts=sum(len(t['expectedSemanticFacts']) for t in corpus['tasks']);recalled=facts-v['missing'];return {'runId':record['runId'],'surface':record['surface'],'taskCount':total,'raw':{'outputCorrectTasks':v['output_correct'],'firstPassSuccessTasks':v['first_pass'],'firstPassParseTasks':v['first_parse'],'firstPassSemanticValidationTasks':v['first_semantic'],'firstPassCompileTasks':v['first_compile'],'missingFacts':v['missing'],'falseAssumptions':v['false'],'invalidCombinations':v['invalid'],'retries':v['retries'],'errors':v['errors'],'inventedSyntax':v['invented'],'wrongPlacement':v['wrong'],'regressions':v['regressions'],'diagnostics':v['diagnostics'],'sourceLines':v['source_lines'],'filesTouched':v['files'],'linesAdded':v['added'],'linesDeleted':v['deleted'],'unnecessaryEdits':v['unnecessary'],'expectedSemanticFacts':facts,'recalledSemanticFacts':recalled},'rates':{'outputCorrectness':_ratio(v['output_correct'],total),'firstPassSuccess':_ratio(v['first_pass'],total),'firstPassParse':_ratio(v['first_parse'],total),'firstPassSemanticValidation':_ratio(v['first_semantic'],total),'firstPassCompile':_ratio(v['first_compile'],total),'inventedSyntaxTaskEventRate':_ratio(v['invented'],total),'wrongPlacementTaskEventRate':_ratio(v['wrong'],total),'semanticFactRecall':_ratio(recalled,facts),'diagnosticsPer100SourceLines':0.0 if v['source_lines']==0 else v['diagnostics']*100.0/v['source_lines']},'tokenCost':{'availableTasks':v['tok_avail'],'unavailableTasks':v['tok_unavail'],'inputTokens':v['input'],'outputTokens':v['output'],'totalTokens':v['input']+v['output']},'humanRewrite':{n:rewrite.get(n,0) for n in HUMAN_REWRITE},'rawFailures':raw}
def compare_runs(before,candidate,corpus=None,baseline=None):
 if corpus is None or baseline is None:corpus,baseline=validate_frozen_prerequisite()
 validate_run_record(before,corpus,baseline);validate_run_record(candidate,corpus,baseline);_require(before['surface']=='current','before run must use current surface');_require(candidate['surface']=='candidate','candidate run must use candidate surface');status=prototype_candidate_status(corpus);_require(status['ready'],'candidate comparison unavailable: integrated E3-E7 prototype coverage is incomplete');a=summarize_run(before,corpus,baseline);b=summarize_run(candidate,corpus,baseline);return {'before':a,'candidate':b,'rawDeltaCandidateMinusBefore':{k:b['raw'][k]-a['raw'][k] for k in a['raw']},'rateDeltaCandidateMinusBefore':{k:b['rates'][k]-a['rates'][k] for k in a['rates']},'interpretation':'raw deltas only; no preferred-language conclusion is implied'}
def fingerprint_run_record(record):r=dict(record);r['fingerprint']=_canonical_fingerprint(r);return r
def main(argv=None):
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);sub.add_parser('verify');s=sub.add_parser('summarize');s.add_argument('record',type=Path);c=sub.add_parser('compare');c.add_argument('before',type=Path);c.add_argument('candidate',type=Path);a=p.parse_args(argv);corpus,baseline=validate_frozen_prerequisite()
 if a.command=='verify':
  st=prototype_candidate_status(corpus);print(json.dumps({'corpusId':corpus['corpusId'],'corpusFingerprint':corpus['fingerprint'],'taskCount':corpus['taskCount'],'baselineId':baseline['baselineId'],'baselineFingerprint':baseline['fingerprint'],'candidateReady':st['ready'],'candidateUnavailableTaskCount':st['unavailableTaskCount'],'candidateBlockers':st['blockers']},indent=2,sort_keys=True));return 0
 if a.command=='summarize':print(json.dumps(summarize_run(_load(a.record),corpus,baseline),indent=2,sort_keys=True));return 0
 print(json.dumps(compare_runs(_load(a.before),_load(a.candidate),corpus,baseline),indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
