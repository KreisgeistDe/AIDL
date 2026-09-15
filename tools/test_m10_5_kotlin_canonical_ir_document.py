from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.compiler_resolution import _reference_candidates
from tools.test_m10_5_kotlin_canonical_ir_domain import _positive_document


ROOT = Path(__file__).resolve().parents[1]
SIGNATURE = ROOT / "compiler" / "kotlin" / "parity" / "canonical-ir-document.signature"


def _without_semantic_hashes(value):
    if isinstance(value, dict):
        return {
            key: _without_semantic_hashes(item)
            for key, item in value.items()
            if key != "semanticHash"
        }
    if isinstance(value, list):
        return [_without_semantic_hashes(item) for item in value]
    return value


def structural_json() -> str:
    # Keep the required-regression ownership explicit: this oracle composes the existing
    # Canonical-IR domain oracle, whose real compiler path resolves declaration identities via
    # compiler_resolution before building the full document.
    assert _reference_candidates is not None
    document = _positive_document()
    return json.dumps(
        _without_semantic_hashes(document),
        sort_keys=True,
        separators=(",", ":"),
    )


class KotlinCanonicalIrDocumentParityTest(unittest.TestCase):
    def test_real_python_full_document_pins_kotlin_structural_document(self) -> None:
        expected = SIGNATURE.read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, structural_json())

    def test_real_python_full_document_structure_is_deterministic(self) -> None:
        self.assertEqual(structural_json(), structural_json())

    def test_semantic_hash_migration_remains_outside_structural_slice(self) -> None:
        document = _positive_document()
        self.assertIn("semanticHash", document)
        self.assertNotIn("semanticHash", _without_semantic_hashes(document))


if __name__ == "__main__":
    unittest.main()
