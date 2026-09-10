from __future__ import annotations

import json
import pathlib
import unittest

from tools.m16_5_candidate_projection import exact_context, project_source

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "fixtures/m16-5/evaluation-candidate-projection-cases.json").read_text(
        encoding="utf-8"
    )
)


class CandidateProjectionDeterminismTests(unittest.TestCase):
    def test_every_independent_candidate_projection_is_deterministic(self):
        context = exact_context()
        for item in CASES["normalization_rows"]:
            with self.subTest(row=item["id"]):
                first = project_source(item["candidate"], context=context)
                second = project_source(item["candidate"], context=context)
                self.assertEqual(first, second)
                self.assertEqual(first.source, second.source)


if __name__ == "__main__":
    unittest.main()
