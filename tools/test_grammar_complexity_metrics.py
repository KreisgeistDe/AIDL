from __future__ import annotations

import json
import unittest

from tools.grammar_complexity_metrics import GRAMMAR, ebnf_sections, measure, productions


class GrammarComplexityMetricsTests(unittest.TestCase):
    def test_metrics_are_deterministic_and_cover_normative_grammar(self) -> None:
        first = measure(GRAMMAR)
        second = measure(GRAMMAR)
        self.assertEqual(first, second)
        self.assertEqual(4, first["contract_revision"])
        self.assertGreater(first["ebnf_sections"], 0)
        self.assertGreater(first["productions"], 0)
        self.assertGreater(first["production_alternatives"], 0)
        self.assertGreater(first["surface_signatures"], 0)
        self.assertEqual(48, first["top_level_declaration_productions"])
        self.assertEqual(48, first["concrete_top_level_forms"])
        self.assertEqual(48, len(first["declaration_productions"]))
        self.assertIn("alias", first["declaration_productions"])
        self.assertIn("entity", first["declaration_productions"])
        self.assertIn("query", first["declaration_productions"])
        self.assertIn("mutation", first["declaration_productions"])
        self.assertNotIn("opaque", first["declaration_productions"])
        print("GRAMMAR_COMPLEXITY_METRICS=" + json.dumps(first, sort_keys=True))

    def test_canonical_projection_productions_are_counted(self) -> None:
        parsed = productions(ebnf_sections(GRAMMAR.read_text(encoding="utf-8")))
        for name in (
            "program",
            "declaration",
            "headerArguments",
            "bodySlot",
            "enumDecl",
            "aliasDecl",
            "entityDecl",
            "queryDecl",
            "mutationDecl",
            "consumerDecl",
            "projectionDecl",
            "clientDecl",
            "migrationDecl",
        ):
            self.assertIn(name, parsed)


if __name__ == "__main__":
    unittest.main()
