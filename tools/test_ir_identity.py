from __future__ import annotations

import ast
import json
import re
import unittest
from dataclasses import dataclass
from pathlib import Path

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_project import compiler_project_from_documents
from tools.ir_identity import (
    IrIdentityError,
    declaration_identities,
    declaration_identity,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spec" / "ir.schema.json"
IDENTITY_PATH = ROOT / "tools" / "ir_identity.py"


def _document(path: str, source: str):
    program, _, _ = parse_text(source)
    return compiler_document_from_ast(Path(path), program)


def _identity_for(source: str, major: int = 1):
    document = _document("source.aidl", source)
    project = compiler_project_from_documents([document])
    return declaration_identity(project.declaration_names[0], major)


@dataclass(frozen=True)
class _FakeModule:
    name: str | None


@dataclass(frozen=True)
class _FakeDeclaration:
    name: str | None


@dataclass(frozen=True)
class _FakeDocument:
    module: _FakeModule | None


@dataclass(frozen=True)
class _FakeProjection:
    document: _FakeDocument
    declaration: _FakeDeclaration
    fully_qualified_name: str | None


class IrIdentityTest(unittest.TestCase):
    def test_identity_uses_existing_fqn_name_module_and_explicit_major(self) -> None:
        identity = _identity_for(
            "module example.orders\nentity Order {\n}\n",
            major=3,
        )

        self.assertEqual("example.orders.Order@3", identity.declaration_id)
        self.assertEqual("example.orders.Order", identity.fqn)
        self.assertEqual("Order", identity.name)
        self.assertEqual("example.orders", identity.owner_module)
        self.assertEqual(
            {
                "declarationId": "example.orders.Order@3",
                "fqn": "example.orders.Order",
                "name": "Order",
                "ownerModule": "example.orders",
            },
            identity.as_ir_fields(),
        )

    def test_identity_is_stable_across_input_and_file_order(self) -> None:
        first = _document(
            "z-orders.aidl",
            "module example.orders\nentity Order {\n}\n",
        )
        second = _document(
            "a-users.aidl",
            "module example.users\nvalue UserId {\n}\n",
        )

        forward = compiler_project_from_documents([first, second])
        reverse = compiler_project_from_documents([second, first])

        forward_by_fqn = {
            identity.fqn: identity.as_ir_fields()
            for identity in declaration_identities(forward.declaration_names, 2)
        }
        reverse_by_fqn = {
            identity.fqn: identity.as_ir_fields()
            for identity in declaration_identities(reverse.declaration_names, 2)
        }
        self.assertEqual(forward_by_fqn, reverse_by_fqn)

    def test_fqn_or_major_change_changes_declaration_id(self) -> None:
        original = _identity_for(
            "module example.orders\nentity Order {\n}\n",
            major=1,
        )
        new_major = _identity_for(
            "module example.orders\nentity Order {\n}\n",
            major=2,
        )
        renamed = _identity_for(
            "module example.orders\nentity PurchaseOrder {\n}\n",
            major=1,
        )
        moved = _identity_for(
            "module example.sales\nentity Order {\n}\n",
            major=1,
        )

        self.assertNotEqual(original.declaration_id, new_major.declaration_id)
        self.assertNotEqual(original.declaration_id, renamed.declaration_id)
        self.assertNotEqual(original.declaration_id, moved.declaration_id)
        self.assertEqual(original.fqn, new_major.fqn)

    def test_generated_identity_matches_schema_id_and_fqn_forms(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        identity = _identity_for(
            "module example.catalog\nentity Pet {\n}\n",
            major=12,
        )

        id_pattern = schema["$defs"]["id"]["pattern"]
        fqn_pattern = schema["$defs"]["fqn"]["pattern"]
        self.assertIsNotNone(re.fullmatch(id_pattern, identity.declaration_id))
        self.assertIsNotNone(re.fullmatch(fqn_pattern, identity.fqn))
        self.assertIsNotNone(re.fullmatch(fqn_pattern, identity.owner_module))

    def test_duplicate_fqns_are_not_disambiguated_or_collapsed(self) -> None:
        first = _document(
            "a.aidl",
            "module example.catalog\nentity Pet {\n}\n",
        )
        second = _document(
            "b.aidl",
            "module example.catalog\nvalue Pet {\n}\n",
        )
        project = compiler_project_from_documents([first, second])

        identities = declaration_identities(project.declaration_names, 4)
        self.assertEqual(2, len(identities))
        self.assertEqual(identities[0], identities[1])
        self.assertEqual("example.catalog.Pet@4", identities[0].declaration_id)

    def test_missing_or_inconsistent_projection_is_rejected_without_synthesis(self) -> None:
        cases = (
            _FakeProjection(
                document=_FakeDocument(module=_FakeModule("example.catalog")),
                declaration=_FakeDeclaration("Pet"),
                fully_qualified_name=None,
            ),
            _FakeProjection(
                document=_FakeDocument(module=None),
                declaration=_FakeDeclaration("Pet"),
                fully_qualified_name="example.catalog.Pet",
            ),
            _FakeProjection(
                document=_FakeDocument(module=_FakeModule("example.catalog")),
                declaration=_FakeDeclaration(None),
                fully_qualified_name="example.catalog.Pet",
            ),
            _FakeProjection(
                document=_FakeDocument(module=_FakeModule("example.catalog")),
                declaration=_FakeDeclaration("Pet"),
                fully_qualified_name="example.other.Pet",
            ),
        )

        for projection in cases:
            with self.subTest(projection=projection):
                with self.assertRaises(IrIdentityError):
                    declaration_identity(projection, 1)

    def test_major_must_be_explicit_positive_integer(self) -> None:
        projection = _FakeProjection(
            document=_FakeDocument(module=_FakeModule("example.catalog")),
            declaration=_FakeDeclaration("Pet"),
            fully_qualified_name="example.catalog.Pet",
        )
        for major in (0, -1, True, 1.5, "1", None):
            with self.subTest(major=major):
                with self.assertRaises(IrIdentityError):
                    declaration_identity(projection, major)  # type: ignore[arg-type]

    def test_boundary_has_no_compiler_or_psi_import_dependency(self) -> None:
        tree = ast.parse(IDENTITY_PATH.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        self.assertTrue(imports.isdisjoint({"tools.compiler_project", "tools.compiler_ast"}))
        self.assertFalse(any("intellij" in name.lower() or "psi" in name.lower() for name in imports))

        projection = _FakeProjection(
            document=_FakeDocument(module=_FakeModule("example.fake")),
            declaration=_FakeDeclaration("Thing"),
            fully_qualified_name="example.fake.Thing",
        )
        self.assertEqual(
            "example.fake.Thing@7",
            declaration_identity(projection, 7).declaration_id,
        )


if __name__ == "__main__":
    unittest.main()
