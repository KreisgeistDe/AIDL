from __future__ import annotations

import ast
import copy
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.ir_semantic_hash import IrSemanticHashError, apply_semantic_hashes
from tools.ir_semantic_projection import prepare_canonical_ir


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spec" / "ir.schema.json"
FIXTURE_PATH = ROOT / "tools" / "ir_schema_contract" / "valid_core.json"
HASH_PATH = ROOT / "tools" / "ir_semantic_hash.py"
_HASH_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


class IrSemanticHashTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.valid_document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _declaration(document: dict, name: str) -> dict:
        return next(item for item in document["declarations"] if item["name"] == name)

    @staticmethod
    def _hashes_by_id(document: dict) -> dict[str, str]:
        return {
            item["declarationId"]: item["semanticHash"]
            for item in document["declarations"]
        }

    def test_populates_schema_valid_document_and_declaration_hashes(self) -> None:
        result = apply_semantic_hashes(self.valid_document)

        self.assertRegex(result["semanticHash"], _HASH_PATTERN)
        self.assertNotEqual("sha256:" + "0" * 64, result["semanticHash"])
        for declaration in result["declarations"]:
            self.assertRegex(declaration["semanticHash"], _HASH_PATTERN)
            self.assertNotEqual("sha256:" + "0" * 64, declaration["semanticHash"])

        validator = Draft202012Validator(
            self.schema,
            format_checker=FormatChecker(),
        )
        errors = sorted(
            validator.iter_errors(result),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        self.assertEqual([], errors, "\n".join(error.message for error in errors))

    def test_is_deterministic_idempotent_and_input_immutable(self) -> None:
        document = copy.deepcopy(self.valid_document)
        before = copy.deepcopy(document)
        first = apply_semantic_hashes(document)
        second = apply_semantic_hashes(first)

        self.assertEqual(before, document)
        self.assertEqual(first, second)
        for _ in range(5):
            self.assertEqual(first, apply_semantic_hashes(document))

    def test_semantic_set_permutations_do_not_change_fingerprints(self) -> None:
        expected = apply_semantic_hashes(self.valid_document)
        document = copy.deepcopy(self.valid_document)
        document["profiles"].reverse()
        document["app"]["auth"]["roles"].reverse()
        document["app"]["auth"]["scopes"].reverse()

        mutation = self._declaration(document, "renamePet")
        mutation["errorIds"].reverse()
        topic = next(item for item in document["declarations"] if item["kind"] == "topic")
        topic["eventIds"].reverse()

        service = document["system"]["services"][0]
        for key in ("owns", "uses", "exposes", "runs"):
            service[key].reverse()
        document["system"]["resources"][0]["transactionIsolation"].reverse()
        document["system"]["topicIds"].reverse()
        document["system"]["apiIds"].reverse()
        document["system"]["consumerGroups"][0]["consumerIds"].reverse()

        actual = apply_semantic_hashes(document)
        self.assertEqual(expected["semanticHash"], actual["semanticHash"])
        self.assertEqual(self._hashes_by_id(expected), self._hashes_by_id(actual))

    def test_source_map_and_existing_hash_values_are_not_hash_inputs(self) -> None:
        expected = apply_semantic_hashes(self.valid_document)
        document = copy.deepcopy(self.valid_document)
        document["semanticHash"] = "sha256:" + "f" * 64
        for declaration in document["declarations"]:
            declaration["semanticHash"] = "sha256:" + "e" * 64

        entry = document["sourceMap"]["entries"][0]
        entry["span"]["file"] = "different/location.aidl"
        entry["span"]["startLine"] += 100
        entry["span"]["endLine"] += 100

        actual = apply_semantic_hashes(document)
        self.assertEqual(expected["semanticHash"], actual["semanticHash"])
        self.assertEqual(self._hashes_by_id(expected), self._hashes_by_id(actual))
        self.assertEqual(document["sourceMap"], actual["sourceMap"])

    def test_m3_05_syntax_variants_compose_to_identical_fingerprints(self) -> None:
        compact = copy.deepcopy(self.valid_document)
        compact["comments"] = ["compact"]
        compact["declarations"][0]["syntaxForm"] = "single-line"

        expanded = copy.deepcopy(self.valid_document)
        expanded["whitespace"] = {"indent": 4}
        expanded["declarations"][0]["rawText"] = "expanded source spelling"
        expanded["sourceMap"]["entries"][0]["span"]["startColumn"] += 2
        expanded["sourceMap"]["entries"][0]["span"]["endColumn"] += 2

        compact_hashed = apply_semantic_hashes(prepare_canonical_ir(compact))
        expanded_hashed = apply_semantic_hashes(prepare_canonical_ir(expanded))
        self.assertEqual(compact_hashed["semanticHash"], expanded_hashed["semanticHash"])
        self.assertEqual(
            self._hashes_by_id(compact_hashed),
            self._hashes_by_id(expanded_hashed),
        )

    def test_semantic_positional_change_changes_document_and_declaration_hash(self) -> None:
        expected = apply_semantic_hashes(self.valid_document)
        document = copy.deepcopy(self.valid_document)
        self._declaration(document, "renamePet")["rootEffect"]["steps"].reverse()

        actual = apply_semantic_hashes(document)
        self.assertNotEqual(expected["semanticHash"], actual["semanticHash"])
        self.assertNotEqual(
            self._declaration(expected, "renamePet")["semanticHash"],
            self._declaration(actual, "renamePet")["semanticHash"],
        )

    def test_profile_extension_semantics_contribute_to_document_hash(self) -> None:
        expected = apply_semantic_hashes(self.valid_document)
        document = copy.deepcopy(self.valid_document)
        document["profileExtensions"]["test@1"] = [
            {
                "target": "/declarations/0",
                "schema": "https://example.test/profile.json",
                "value": {"mode": "strict"},
            }
        ]

        actual = apply_semantic_hashes(document)
        self.assertNotEqual(expected["semanticHash"], actual["semanticHash"])
        self.assertEqual(self._hashes_by_id(expected), self._hashes_by_id(actual))

    def test_invalid_boundary_shapes_and_versions_are_rejected(self) -> None:
        with self.assertRaises(IrSemanticHashError):
            apply_semantic_hashes([])  # type: ignore[arg-type]
        with self.assertRaises(IrSemanticHashError):
            apply_semantic_hashes({"irVersion": "0.3.0", "declarations": {}})
        with self.assertRaises(IrSemanticHashError):
            apply_semantic_hashes({"irVersion": "0.3.0", "declarations": ["bad"]})
        with self.assertRaises(IrSemanticHashError):
            apply_semantic_hashes({"irVersion": "v0.3.0", "declarations": []})

    def test_boundary_has_no_compiler_cli_or_psi_dependency(self) -> None:
        tree = ast.parse(HASH_PATH.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertFalse(
            any(
                "compiler" in name
                or "intellij" in name
                or "psi" in name
                or "cli" in name
                or "plan" in name
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
