from __future__ import annotations

import copy
import json
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

    def test_revision4_operation_contract_is_historical_not_active_grammar(self) -> None:
        contract = json.loads(
            (classification.ROOT / "spec/language-surface-v1.json").read_text(encoding="utf-8")
        )
        transition = json.loads(
            (classification.ROOT / "spec/core-authority-transition-v1.json").read_text(encoding="utf-8")
        )
        grammar = (classification.ROOT / "docs/06-grammar.md").read_text(encoding="utf-8")
        declarations = {item["kind"]: item for item in contract["declaration_kinds"]}
        for kind in ("query", "mutation"):
            self.assertEqual(
                [item["name"] for item in declarations[kind]["header_args"]],
                ["parameters"],
            )
        historical = {item["path"]: item for item in transition["historicalAuthorities"]}
        self.assertFalse(historical["spec/language-surface-v1.json"]["activeLanguageAuthority"])
        self.assertIn("historical", historical["spec/m10-2-language-surface-classification.json"]["currentRole"])
        self.assertNotIn("### Query and mutation", grammar)
        self.assertIn("P2+ migration boundary", grammar)

    def test_r5_reference_surfaces_do_not_present_revision4_as_active_authority(self) -> None:
        grammar = (classification.ROOT / "docs/06-grammar.md").read_text(encoding="utf-8")
        self.assertIn("The active AIDL language authority is `spec/core-self-description-v1.aidl`", grammar)
        self.assertIn("deterministic human-readable projection", grammar)

        reference_surfaces = [
            "examples/calendar-offline/README.md",
            "examples/petstore/README.md",
            "examples/videohub/README.md",
            "fixtures/README.md",
        ]
        for relative in reference_surfaces:
            text = (classification.ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("spec/core-self-description-v1.aidl", text, relative)
            self.assertIn("Recovery R5 Authority", text, relative)

        petstore = (classification.ROOT / "examples/petstore/README.md").read_text(encoding="utf-8")
        self.assertNotIn("Revision 4 bleibt die semantische Authority", petstore)
        fixtures = (classification.ROOT / "fixtures/README.md").read_text(encoding="utf-8")
        self.assertIn("they are not by themselves positive evidence for current Core syntax", fixtures)

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
