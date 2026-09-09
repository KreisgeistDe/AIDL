from __future__ import annotations

import json
import unittest

from tools.grammar_complexity_metrics import GRAMMAR, ebnf_sections, measure, productions


class GrammarComplexityMetricsTests(unittest.TestCase):
    def test_metrics_are_deterministic_and_cover_normative_grammar(self) -> None:
        first = measure(GRAMMAR)
        second = measure(GRAMMAR)
        self.assertEqual(first, second)
        self.assertEqual(16, first["ebnf_sections"])
        self.assertEqual(211, first["productions"])
        self.assertEqual(522, first["production_alternatives"])
        self.assertEqual(321, first["surface_signatures"])
        self.assertEqual(48, first["top_level_declaration_productions"])
        self.assertEqual(49, first["concrete_top_level_forms"])
        self.assertEqual(
            {
                "arrow_alternatives": 3,
                "block_alternatives": 70,
                "colon_alternatives": 46,
                "equals_alternatives": 6,
                "leaf_alternatives": 129,
                "list_alternatives": 20,
                "profile_property_alternatives": 39,
                "test_statement_alternatives": 4,
                "ui_statement_alternatives": 16,
            },
            first["structural_markers"],
        )
        self.assertIn("profileProperty", first["inline_block_dual_productions"])
        self.assertIn("idempotencyClause", first["inline_block_dual_productions"])
        print("GRAMMAR_COMPLEXITY_METRICS=" + json.dumps(first, sort_keys=True))

    def test_multiline_production_headers_are_counted(self) -> None:
        parsed = productions(ebnf_sections(GRAMMAR.read_text(encoding="utf-8")))
        for name in (
            "constraintArguments",
            "equalityExpression",
            "operationSignature",
            "idempotencyClause",
            "transactionStatement",
            "workflowStatement",
            "deploymentClause",
            "nativeFunctionDecl",
        ):
            self.assertIn(name, parsed)


if __name__ == "__main__":
    unittest.main()
