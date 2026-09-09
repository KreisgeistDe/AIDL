from __future__ import annotations

import json
import pathlib
import unittest

from tools.m16_5_e3_prototype import (
    CANDIDATE_SCHEMA_VERSION,
    Cardinality,
    ConstructionError,
    ContextualTerminal,
    WholeNodeAlternative,
    build_catalog,
    parse_candidate,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "fixtures/m16-5/e3-cases.json").read_text())


class E3PrototypeTests(unittest.TestCase):
    def parse(self, source: str):
        return parse_candidate(
            source,
            source_version=CANDIDATE_SCHEMA_VERSION,
            schema_version=CANDIDATE_SCHEMA_VERSION,
        )

    def assert_code(
        self,
        source: str,
        code: str,
        *,
        source_version: str = CANDIDATE_SCHEMA_VERSION,
        schema_version: str | None = None,
    ):
        with self.assertRaises(ConstructionError) as caught:
            parse_candidate(
                source,
                source_version=source_version,
                schema_version=schema_version or source_version,
            )
        self.assertEqual(caught.exception.diagnostic.code, code)

    def test_all_nine_normalization_rows_construct(self):
        self.assertEqual(len(CASES["normalization_rows"]), 9)
        for case in CASES["normalization_rows"]:
            with self.subTest(case=case["id"]):
                result = self.parse(case["source"])
                self.assertEqual(result.sidecar.source, case["source"])
                self.assertTrue(result.node.values)

    def test_representative_existing_families_construct(self):
        for case in CASES["representative_families"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(self.parse(case["source"]).node.kind, case["id"])

    def test_lossless_sidecar_preserves_comments_whitespace_lexemes_and_anchors(self):
        source = (
            "projection P { // header\n"
            "\t source: OrderCreated // keep\n"
            "  target: CustomerView\n"
            "}\n"
        )
        result = self.parse(source)
        self.assertEqual(result.sidecar.source, source)
        self.assertEqual("".join(token.lexeme for token in result.sidecar.tokens), source)
        self.assertIn("// keep", [token.lexeme for token in result.sidecar.tokens])
        self.assertTrue(
            any(anchor.role == "body:target" for anchor in result.sidecar.anchors)
        )

    def test_stale_or_mismatched_source_schema_version_fails_closed(self):
        source = CASES["normalization_rows"][0]["source"]
        self.assert_code(source, "AIDL-S008", source_version="e2-old")
        self.assert_code(source, "AIDL-S008", schema_version="stale-schema")

    def test_legacy_forms_are_rejected(self):
        for source in CASES["legacy_rejections"]:
            with self.subTest(source=source.splitlines()[0]):
                self.assert_code(source, "AIDL-S007")

    def test_ui_and_test_statement_are_intentionally_excluded(self):
        self.assert_code("uiStatement U {\n}\n", "AIDL-S005")
        self.assert_code("testStatement T {\n}\n", "AIDL-S005")

    def test_structural_diagnostic_namespace_and_cardinality(self):
        self.assert_code(
            "client C {\n  service: S\n  service: T\n}\n", "AIDL-S002"
        )
        self.assert_code("client C {\n  mystery: S\n}\n", "AIDL-S003")
        self.assert_code("client C {\n}\n", "AIDL-S001")
        self.assert_code(
            'migration M {\n  from: v1\n  to: "v2"\n}\n', "AIDL-S004"
        )

    def test_catalog_materialization_is_process_cached(self):
        build_catalog.cache_clear()
        first = build_catalog()
        second = build_catalog()
        self.assertIs(first, second)
        info = build_catalog.cache_info()
        self.assertEqual(info.misses, 1)
        self.assertGreaterEqual(info.hits, 1)

    def test_all_e1_combinator_concepts_are_exercised(self):
        catalog = build_catalog()
        self.assertTrue(
            any(
                shape.alternatives
                and isinstance(shape.alternatives[0], WholeNodeAlternative)
                for shape in catalog.shapes.values()
            )
        )
        self.assertTrue(all(shape.ordered_slots for shape in catalog.enabled_shapes()))
        self.assertTrue(
            any(
                any(
                    child.named
                    and isinstance(child.contextual_terminal, ContextualTerminal)
                    for child in shape.keyed_children
                )
                for shape in catalog.shapes.values()
            )
        )
        self.assertTrue(
            any(
                any(child.cardinality is Cardinality.MANY for child in shape.keyed_children)
                for shape in catalog.shapes.values()
            )
        )

    def test_candidate_semantics_stable_under_trivia_changes(self):
        first = self.parse("projection P {\n  source: E\n  target: V\n}\n").node
        second = self.parse(
            "projection P { // comment\n\n  source: E\n  target: V\n}\n"
        ).node
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
