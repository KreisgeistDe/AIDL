from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tools import m10_2_language_surface_classification as classification


class LanguageSurfaceClassificationTest(unittest.TestCase):
    def test_repository_inventory_is_exhaustive_and_deterministic(self) -> None:
        first = classification.validate()
        second = classification.validate()
        manifest = classification._load(classification.ROOT / classification.MANIFEST)
        self.assertEqual(first, second)
        self.assertGreater(first["source_count"], 57)
        self.assertEqual(first["document_count"], len(manifest["document_surfaces"]))
        self.assertEqual(first["contract_revision"], 4)
        self.assertGreater(first["source_classes"]["legacy-readable-compatibility"], 0)
        self.assertGreater(first["source_classes"]["negative-rejection-fixture"], 0)

    def test_new_unclassified_aidl_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "spec").mkdir(parents=True)
            (root / "new").mkdir(parents=True)
            (root / "spec/language-surface-v1.json").write_text(
                '{"authority":"M10.1","status":"frozen","contract_revision":4}', encoding="utf-8"
            )
            (root / "new/unclassified.aidl").write_text("entity X {}", encoding="utf-8")
            manifest = {
                "schema_version": classification.SCHEMA_VERSION,
                "authority": "M10.2-01",
                "classes": sorted(classification.CLASSES),
                "frozen_language_contract": {
                    "path": "spec/language-surface-v1.json",
                    "authority": "M10.1",
                    "status": "frozen",
                    "contract_revision": 4,
                },
                "source_rules": [],
                "document_surfaces": [],
                "required_document_surfaces": [],
                "m10_3_mismatches": ["x"],
            }
            with self.assertRaisesRegex(ValueError, "exactly one classification rule"):
                classification.validate(root, manifest)

    def test_duplicate_source_classification_fails_closed(self) -> None:
        manifest = classification._load(classification.ROOT / classification.MANIFEST)
        mutated = copy.deepcopy(manifest)
        mutated["source_rules"].append(
            {
                "id": "duplicate-examples",
                "pattern": "^examples/.*\\.aidl$",
                "class": "illustrative-aspirational",
            }
        )
        with self.assertRaisesRegex(ValueError, "exactly one classification rule"):
            classification.validate(manifest=mutated)

    def test_document_classification_drift_fails_closed(self) -> None:
        manifest = classification._load(classification.ROOT / classification.MANIFEST)
        mutated = copy.deepcopy(manifest)
        mutated["document_surfaces"] = mutated["document_surfaces"][:-1]
        with self.assertRaisesRegex(ValueError, "document classification drift"):
            classification.validate(manifest=mutated)

    def test_frozen_contract_revision_drift_fails_closed(self) -> None:
        manifest = classification._load(classification.ROOT / classification.MANIFEST)
        mutated = copy.deepcopy(manifest)
        mutated["frozen_language_contract"]["contract_revision"] = 999
        with self.assertRaisesRegex(ValueError, "frozen M10.1 contract identity drift"):
            classification.validate(manifest=mutated)


if __name__ == "__main__":
    unittest.main()
