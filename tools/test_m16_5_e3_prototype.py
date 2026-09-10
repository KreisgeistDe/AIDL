from __future__ import annotations
import json, pathlib, unittest
from tools.m16_5_e3_prototype import CANDIDATE_SCHEMA_VERSION, Cardinality, ConstructionError, ContextualTerminal, WholeNodeAlternative, build_catalog, parse_candidate
ROOT=pathlib.Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/"fixtures/m16-5/e3-cases.json").read_text())
class E3PrototypeTests(unittest.TestCase):
    def parse(self,source): return parse_candidate(source,source_version=CANDIDATE_SCHEMA_VERSION,schema_version=CANDIDATE_SCHEMA_VERSION)
    def assert_code(self,source,code,*,source_version=CANDIDATE_SCHEMA_VERSION,schema_version=None):
        with self.assertRaises(ConstructionError) as caught: parse_candidate(source,source_version=source_version,schema_version=schema_version or source_version)
        self.assertEqual(caught.exception.diagnostic.code,code)
    def test_all_nine_normalization_rows_construct(self):
        self.assertEqual(len(CASES["normalization_rows"]),9)
        for case in CASES["normalization_rows"]:
            with self.subTest(case=case["id"]): self.assertTrue(self.parse(case["source"]).node.values)
    def test_former_fact_gaps_are_fact_complete_in_v2(self):
        cat=build_catalog()
        expected={
          "projection":(("projection","multi-source-projection"),("projection","source","target")),
          "index":(("index-direction",),("index","indexField")),
          "queue_deadletter":(("dead-letter-threshold",),("topic","queue","deadLetterAttempts")),
          "schedule_lease":(("schedule-lease",),("schedule","singleton","lease")),
          "sync_outbox":(("sync-outbox",),("sync","changesTarget","changesDelivery")),
        }
        for kind,(surfaces,facts) in expected.items():
            shape=cat.shape(kind); self.assertEqual(shape.semantic_surfaces,surfaces); self.assertEqual(shape.semantic_fact_prefixes,facts)
        p=self.parse(CASES["multi_source_projection"]).node
        self.assertEqual(p.values["source"],["Order","Payment"])
        idx=self.parse(next(x["source"] for x in CASES["normalization_rows"] if x["id"]=="explicit-index")).node
        self.assertEqual(idx.values["fields"],[("email","asc"),("tenantId","desc")])
    def test_representative_existing_families_construct(self):
        for case in CASES["representative_families"]: self.assertEqual(self.parse(case["source"]).node.kind,case["id"])
    def test_lossless_sidecar_preserves_comments_whitespace_lexemes_and_anchors(self):
        source="projection P { // header\n\t source: OrderCreated // keep\n  target: CustomerView\n}\n"
        r=self.parse(source); self.assertEqual("".join(t.lexeme for t in r.sidecar.tokens),source); self.assertTrue(any(a.role=="body:target" for a in r.sidecar.anchors))
    def test_stale_or_mismatched_source_schema_version_fails_closed(self):
        s=CASES["normalization_rows"][0]["source"]; self.assert_code(s,"AIDL-S008",source_version="e2-old"); self.assert_code(s,"AIDL-S008",schema_version="stale-schema")
    def test_legacy_forms_are_rejected(self):
        for source in CASES["legacy_rejections"]: self.assert_code(source,"AIDL-S007")
    def test_ui_and_test_statement_are_intentionally_excluded(self):
        self.assert_code("uiStatement U {\n}\n","AIDL-S005"); self.assert_code("testStatement T {\n}\n","AIDL-S005")
    def test_structural_diagnostic_namespace_and_cardinality(self):
        self.assert_code("client C {\n  service: S\n  service: T\n}\n","AIDL-S002"); self.assert_code("client C {\n  mystery: S\n}\n","AIDL-S003"); self.assert_code("client C {\n}\n","AIDL-S001")
    def test_catalog_materialization_is_process_cached(self):
        build_catalog.cache_clear(); a=build_catalog(); b=build_catalog(); self.assertIs(a,b); self.assertEqual(build_catalog.cache_info().misses,1)
    def test_all_e1_combinator_concepts_are_exercised(self):
        c=build_catalog(); self.assertTrue(any(s.alternatives and isinstance(s.alternatives[0],WholeNodeAlternative) for s in c.shapes.values())); self.assertTrue(all(s.ordered_slots for s in c.enabled_shapes())); self.assertTrue(any(any(ch.named and isinstance(ch.contextual_terminal,ContextualTerminal) for ch in s.keyed_children) for s in c.shapes.values())); self.assertTrue(any(any(ch.cardinality is Cardinality.MANY for ch in s.keyed_children) for s in c.shapes.values()))
    def test_candidate_semantics_stable_under_trivia_changes(self):
        self.assertEqual(self.parse("projection P {\n  source: E\n  target: V\n}\n").node,self.parse("projection P { // c\n\n  source: E\n  target: V\n}\n").node)
if __name__=="__main__": unittest.main()
