from __future__ import annotations

import ast
import copy
import unittest
from pathlib import Path

from tools.ir_canonical_json import canonical_ir_json_bytes
from tools.ir_defaults import IrDefaultError, materialize_semantic_defaults


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_PATH = ROOT / "tools" / "ir_defaults.py"


def _identity(kind: str) -> dict[str, object]:
    return {
        "declarationId": f"example.Thing@1",
        "fqn": "example.Thing",
        "name": "Thing",
        "ownerModule": "example",
        "semanticHash": "sha256:" + "0" * 64,
        "kind": kind,
    }


class IrDefaultsTest(unittest.TestCase):
    def test_omitted_and_explicit_field_defaults_have_identical_canonical_ir(self) -> None:
        field = {
            "name": "id",
            "type": {"kind": "scalar", "name": "uuid"},
            "required": True,
            "mutable": False,
            "sensitive": False,
            "generated": False,
        }
        omitted = {"declarations": [{**_identity("entity"), "fields": [field], "identityFields": ["id"]}]}
        explicit = copy.deepcopy(omitted)
        explicit["declarations"][0]["fields"][0].update(
            primary=False, concurrencyToken=False, onDelete="none"
        )

        omitted_ir = materialize_semantic_defaults(omitted)
        explicit_ir = materialize_semantic_defaults(explicit)
        self.assertEqual(explicit_ir, omitted_ir)
        self.assertEqual(canonical_ir_json_bytes(explicit_ir), canonical_ir_json_bytes(omitted_ir))

    def test_materializes_field_defaults_for_all_field_bearing_declarations(self) -> None:
        base_field = {
            "name": "value", "type": {"kind": "scalar", "name": "string"},
            "required": True, "mutable": False, "sensitive": False, "generated": False,
        }
        document = {"declarations": [
            {**_identity("value"), "fields": [base_field]},
            {**_identity("entity"), "fields": [base_field], "identityFields": ["value"]},
            {**_identity("event"), "majorVersion": 1, "fields": [base_field]},
        ]}
        result = materialize_semantic_defaults(document)
        for declaration in result["declarations"]:
            self.assertEqual(False, declaration["fields"][0]["primary"])
            self.assertEqual(False, declaration["fields"][0]["concurrencyToken"])
            self.assertEqual("none", declaration["fields"][0]["onDelete"])

    def test_explicit_non_default_field_values_are_preserved(self) -> None:
        document = {"declarations": [{**_identity("entity"), "identityFields": ["id"], "fields": [{
            "name": "id", "type": {"kind": "scalar", "name": "uuid"},
            "required": True, "mutable": False, "sensitive": True, "generated": True,
            "primary": True, "concurrencyToken": True, "onDelete": "cascade",
        }]}]}
        self.assertEqual(document, materialize_semantic_defaults(document))

    def test_omitted_and_explicit_no_retry_are_identical(self) -> None:
        omitted = {"declarations": [{**_identity("workflow"), "input": {}, "output": {}, "steps": []}]}
        explicit = copy.deepcopy(omitted)
        explicit["declarations"][0]["retry"] = {"kind": "none"}
        self.assertEqual(
            materialize_semantic_defaults(explicit),
            materialize_semantic_defaults(omitted),
        )

    def test_is_deterministic_idempotent_and_does_not_mutate_input(self) -> None:
        document = {"declarations": [{**_identity("task"), "input": {}, "output": {}, "steps": []}]}
        original = copy.deepcopy(document)
        first = materialize_semantic_defaults(document)
        self.assertEqual(original, document)
        self.assertEqual(first, materialize_semantic_defaults(document))
        self.assertEqual(first, materialize_semantic_defaults(first))

    def test_rejects_invalid_boundary_shapes(self) -> None:
        for document in ({}, {"declarations": {}}, {"declarations": [None]}):
            with self.subTest(document=document), self.assertRaises(IrDefaultError):
                materialize_semantic_defaults(document)

    def test_boundary_has_no_compiler_or_psi_dependency(self) -> None:
        tree = ast.parse(DEFAULTS_PATH.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertFalse(any("compiler" in name or "intellij" in name or "psi" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
