from __future__ import annotations

import ast
import copy
import unittest
from pathlib import Path

from tools.ir_canonical_json import canonical_ir_json_bytes
from tools.ir_defaults import IrDefaultError
from tools.ir_semantic_projection import (
    IrSemanticProjectionError,
    prepare_canonical_ir,
)


ROOT = Path(__file__).resolve().parents[1]
PROJECTION_PATH = ROOT / "tools" / "ir_semantic_projection.py"


def _field() -> dict[str, object]:
    return {
        "name": "id",
        "type": {"kind": "scalar", "name": "uuid"},
        "required": True,
        "mutable": False,
        "sensitive": False,
        "generated": False,
    }


def _document() -> dict[str, object]:
    return {
        "declarations": [
            {
                "kind": "entity",
                "declarationId": "example.Pet@1",
                "fqn": "example.Pet",
                "name": "Pet",
                "ownerModule": "example",
                "semanticHash": "sha256:" + "0" * 64,
                "fields": [_field()],
                "identityFields": ["id"],
            }
        ],
        "sourceMap": {
            "entries": [
                {
                    "nodePath": "/declarations/0",
                    "originalDeclarationId": "example.Pet@1",
                    "span": {
                        "file": "pet.aidl",
                        "startLine": 1,
                        "startColumn": 1,
                        "endLine": 3,
                        "endColumn": 2,
                    },
                }
            ]
        },
        "profileExtensions": {},
    }


class IrSemanticProjectionTest(unittest.TestCase):
    def test_syntax_variants_produce_identical_canonical_ir(self) -> None:
        compact = _document()
        compact["comments"] = ["compact"]
        compact["declarations"][0]["syntaxForm"] = "single-line"
        compact["declarations"][0]["fields"][0]["punctuation"] = "colon"

        expanded = _document()
        expanded["whitespace"] = {"indent": 4}
        expanded["declarations"][0]["clauseOrder"] = ["identity", "fields"]
        expanded["declarations"][0]["fields"][0]["rawText"] = "id : uuid"

        self.assertEqual(prepare_canonical_ir(compact), prepare_canonical_ir(expanded))
        self.assertEqual(
            canonical_ir_json_bytes(prepare_canonical_ir(compact)),
            canonical_ir_json_bytes(prepare_canonical_ir(expanded)),
        )

    def test_semantically_relevant_differences_remain(self) -> None:
        first = _document()
        second = _document()
        second["declarations"][0]["fields"][0]["sensitive"] = True
        self.assertNotEqual(prepare_canonical_ir(first), prepare_canonical_ir(second))
        self.assertNotEqual(
            canonical_ir_json_bytes(prepare_canonical_ir(first)),
            canonical_ir_json_bytes(prepare_canonical_ir(second)),
        )

    def test_preserves_ordered_arrays_source_maps_and_profile_payloads(self) -> None:
        document = _document()
        document["declarations"].append(
            {
                "kind": "workflow",
                "declarationId": "example.Flow@1",
                "fqn": "example.Flow",
                "name": "Flow",
                "ownerModule": "example",
                "semanticHash": "sha256:" + "0" * 64,
                "input": {"kind": "record", "fields": []},
                "output": {"kind": "record", "fields": []},
                "steps": [{"stepId": "b", "effect": {}}, {"stepId": "a", "effect": {}}],
            }
        )
        document["profileExtensions"] = {
            "test@1": [
                {
                    "target": "/declarations/0",
                    "schema": "https://example.test/profile.json",
                    "value": {"comments": "profile meaning", "syntaxForm": "profile value"},
                }
            ]
        }
        result = prepare_canonical_ir(document)
        self.assertEqual(document["sourceMap"], result["sourceMap"])
        self.assertEqual(document["profileExtensions"], result["profileExtensions"])
        self.assertEqual(["b", "a"], [step["stepId"] for step in result["declarations"][1]["steps"]])

    def test_unknown_non_syntax_fields_are_not_silently_removed(self) -> None:
        document = _document()
        document["declarations"][0]["unknownMeaning"] = 42
        self.assertEqual(
            42,
            prepare_canonical_ir(document)["declarations"][0]["unknownMeaning"],
        )

    def test_preserves_m3_04_defaults_and_explicit_non_defaults(self) -> None:
        omitted = prepare_canonical_ir(_document())
        explicit_document = _document()
        explicit_document["declarations"][0]["fields"][0].update(
            primary=True, concurrencyToken=True, onDelete="cascade"
        )
        explicit = prepare_canonical_ir(explicit_document)
        self.assertEqual(False, omitted["declarations"][0]["fields"][0]["primary"])
        self.assertEqual("none", omitted["declarations"][0]["fields"][0]["onDelete"])
        self.assertEqual(True, explicit["declarations"][0]["fields"][0]["primary"])
        self.assertEqual("cascade", explicit["declarations"][0]["fields"][0]["onDelete"])

    def test_is_idempotent_and_input_immutable(self) -> None:
        document = _document()
        document["comments"] = ["not semantic"]
        original = copy.deepcopy(document)
        first = prepare_canonical_ir(document)
        self.assertEqual(original, document)
        self.assertEqual(first, prepare_canonical_ir(first))

    def test_invalid_boundary_shapes_are_rejected(self) -> None:
        with self.assertRaises(IrSemanticProjectionError):
            prepare_canonical_ir([])  # type: ignore[arg-type]
        with self.assertRaises(IrDefaultError):
            prepare_canonical_ir({})

    def test_boundary_has_no_compiler_or_psi_dependency(self) -> None:
        tree = ast.parse(PROJECTION_PATH.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertFalse(any("compiler" in name or "intellij" in name or "psi" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
