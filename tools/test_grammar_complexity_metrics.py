from __future__ import annotations

import json
import unittest

from tools.grammar_complexity_metrics import GRAMMAR, measure


class GrammarComplexityMetricsTests(unittest.TestCase):
    def test_metrics_are_deterministic_and_cover_normative_grammar(self) -> None:
        first = measure(GRAMMAR)
        second = measure(GRAMMAR)
        self.assertEqual(first, second)
        self.assertEqual(48, first["top_level_declaration_productions"])
        self.assertEqual(49, first["concrete_top_level_forms"])
        self.assertGreater(first["syntax_word_terminals"], 100)
        self.assertGreater(first["productions"], 100)
        self.assertGreater(first["production_alternatives"], first["productions"])
        self.assertIn("profileProperty", first["inline_block_dual_productions"])
        print("GRAMMAR_COMPLEXITY_METRICS=" + json.dumps(first, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
