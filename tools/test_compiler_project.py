from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_project  # noqa: E402


class CompilerProjectTest(unittest.TestCase):
    def test_loading_preserves_discovery_order_and_indexes_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "z"
            nested.mkdir()
            first = root / "a.aidl"
            second = root / "b.aidl"
            third = nested / "c.aidl"
            first.write_text("module example.shared\nentity First {\n}\n", encoding="utf-8")
            second.write_text("entity Unscoped {\n}\n", encoding="utf-8")
            third.write_text("module example.shared\nentity Third {\n}\n", encoding="utf-8")

            project = compiler_project.load_compiler_project([root, third])

            self.assertEqual(
                [document.source_path for document in project.documents],
                [first, second, third],
            )
            self.assertEqual(list(project.modules), ["example.shared"])
            self.assertEqual(
                [document.source_path for document in project.modules["example.shared"]],
                [first, third],
            )
            self.assertEqual(
                [document.source_path for document in project.documents_without_module],
                [second],
            )

    def test_module_index_order_follows_first_document_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = {
                "a.aidl": "module zeta.module\n",
                "b.aidl": "module alpha.module\n",
                "c.aidl": "module zeta.module\n",
            }
            for name, source in sources.items():
                (root / name).write_text(source, encoding="utf-8")

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(list(project.modules), ["zeta.module", "alpha.module"])
            self.assertEqual(
                [document.source_path.name for document in project.modules["zeta.module"]],
                ["a.aidl", "c.aidl"],
            )

    def test_declaration_names_are_qualified_from_declared_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "names.aidl"
            source.write_text(
                "module example.orders\n"
                "entity Order {\n}\n"
                "value OrderId {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(
                [item.fully_qualified_name for item in project.declaration_names],
                ["example.orders.Order", "example.orders.OrderId"],
            )
            self.assertIs(project.declaration_names[0].document, project.documents[0])
            self.assertIs(
                project.declaration_names[0].declaration,
                project.documents[0].declarations[0],
            )

    def test_declaration_name_order_and_unresolved_syntax_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.aidl"
            second = root / "b.aidl"
            third = root / "c.aidl"
            first.write_text(
                "module example.first\n"
                "entity First {\n}\n"
                "auth {\n}\n"
                "value Second {\n}\n",
                encoding="utf-8",
            )
            second.write_text("entity Unscoped {\n}\n", encoding="utf-8")
            third.write_text(
                "module example.third\nentity Third {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(
                [
                    (
                        item.document.source_path.name,
                        item.declaration.name,
                        item.fully_qualified_name,
                    )
                    for item in project.declaration_names
                ],
                [
                    ("a.aidl", "First", "example.first.First"),
                    ("a.aidl", None, None),
                    ("a.aidl", "Second", "example.first.Second"),
                    ("b.aidl", "Unscoped", None),
                    ("c.aidl", "Third", "example.third.Third"),
                ],
            )
            self.assertEqual(
                [document.source_path.name for document in project.documents_without_module],
                ["b.aidl"],
            )

    def test_explicit_import_resolves_exported_declaration_and_preserves_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer = root / "a-consumer.aidl"
            provider = root / "b-provider.aidl"
            consumer.write_text(
                "module example.consumer\n"
                "import example.provider.PublicType\n"
                "entity Consumer {\n}\n",
                encoding="utf-8",
            )
            provider.write_text(
                "module example.provider\n"
                "export value PublicType {\n}\n"
                "value PrivateType {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(len(project.import_resolutions), 1)
            resolution = project.import_resolutions[0]
            self.assertIs(resolution.document, project.documents[0])
            self.assertIs(resolution.import_, project.documents[0].imports[0])
            self.assertEqual(resolution.import_.name, "example.provider.PublicType")
            self.assertFalse(resolution.import_.wildcard)
            self.assertEqual(
                [item.fully_qualified_name for item in resolution.declarations],
                ["example.provider.PublicType"],
            )
            self.assertIs(resolution.declarations[0], project.declaration_names[1])

    def test_wildcard_import_resolves_only_exports_in_source_declaration_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer = root / "a-consumer.aidl"
            first_provider = root / "b-provider.aidl"
            second_provider = root / "c-provider.aidl"
            consumer.write_text(
                "module example.consumer\n"
                "import example.shared.*\n",
                encoding="utf-8",
            )
            first_provider.write_text(
                "module example.shared\n"
                "export entity First {\n}\n"
                "value Hidden {\n}\n"
                "export value Second {\n}\n",
                encoding="utf-8",
            )
            second_provider.write_text(
                "module example.shared\n"
                "export error Third {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            resolution = project.import_resolutions[0]
            self.assertTrue(resolution.import_.wildcard)
            self.assertEqual(
                [
                    (item.document.source_path.name, item.fully_qualified_name)
                    for item in resolution.declarations
                ],
                [
                    ("b-provider.aidl", "example.shared.First"),
                    ("b-provider.aidl", "example.shared.Second"),
                    ("c-provider.aidl", "example.shared.Third"),
                ],
            )

    def test_import_resolution_preserves_document_import_order_and_unresolved_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            provider = root / "c-provider.aidl"
            first.write_text(
                "module example.first\n"
                "import missing.module.Type\n"
                "import example.provider.*\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "import example.provider.Visible\n"
                "import example.provider.Hidden\n",
                encoding="utf-8",
            )
            provider.write_text(
                "module example.provider\n"
                "export value Visible {\n}\n"
                "value Hidden {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(
                [
                    (
                        resolution.document.source_path.name,
                        resolution.import_.name,
                        resolution.import_.wildcard,
                        [
                            declaration.fully_qualified_name
                            for declaration in resolution.declarations
                        ],
                    )
                    for resolution in project.import_resolutions
                ],
                [
                    ("a-first.aidl", "missing.module.Type", False, []),
                    (
                        "a-first.aidl",
                        "example.provider.*",
                        True,
                        ["example.provider.Visible"],
                    ),
                    (
                        "b-second.aidl",
                        "example.provider.Visible",
                        False,
                        ["example.provider.Visible"],
                    ),
                    ("b-second.aidl", "example.provider.Hidden", False, []),
                ],
            )
            self.assertEqual(
                [import_.name for import_ in project.documents[0].imports],
                ["missing.module.Type", "example.provider.*"],
            )

    def test_direct_module_cycle_is_detected_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.aidl").write_text(
                "module example.a\n"
                "import example.b.BType\n"
                "export value AType {\n}\n",
                encoding="utf-8",
            )
            (root / "b.aidl").write_text(
                "module example.b\n"
                "import example.a.AType\n"
                "export value BType {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(
                [
                    (dependency.source_module, dependency.target_module)
                    for dependency in project.module_dependencies
                ],
                [("example.a", "example.b"), ("example.b", "example.a")],
            )
            self.assertEqual(
                [cycle.modules for cycle in project.module_cycles],
                [("example.a", "example.b")],
            )

    def test_multi_module_cycle_uses_explicit_and_wildcard_import_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.aidl").write_text(
                "module example.a\n"
                "import example.b.*\n"
                "export value AType {\n}\n",
                encoding="utf-8",
            )
            (root / "b.aidl").write_text(
                "module example.b\n"
                "import example.c.CType\n"
                "export value BType {\n}\n",
                encoding="utf-8",
            )
            (root / "c.aidl").write_text(
                "module example.c\n"
                "import example.a.*\n"
                "export value CType {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(
                [
                    (dependency.source_module, dependency.target_module)
                    for dependency in project.module_dependencies
                ],
                [
                    ("example.a", "example.b"),
                    ("example.b", "example.c"),
                    ("example.c", "example.a"),
                ],
            )
            self.assertEqual(
                [cycle.modules for cycle in project.module_cycles],
                [("example.a", "example.b", "example.c")],
            )

    def test_acyclic_graph_remains_valid_and_unresolved_imports_add_no_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.aidl").write_text(
                "module example.a\n"
                "import example.b.Visible\n"
                "import example.b.Hidden\n"
                "import missing.module.Type\n",
                encoding="utf-8",
            )
            (root / "b.aidl").write_text(
                "module example.b\n"
                "import example.c.*\n"
                "export value Visible {\n}\n"
                "value Hidden {\n}\n",
                encoding="utf-8",
            )
            (root / "c.aidl").write_text(
                "module example.c\n"
                "export value CType {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            self.assertEqual(
                [
                    (dependency.source_module, dependency.target_module)
                    for dependency in project.module_dependencies
                ],
                [("example.a", "example.b"), ("example.b", "example.c")],
            )
            self.assertEqual(project.module_cycles, ())
            self.assertEqual(
                [len(resolution.declarations) for resolution in project.import_resolutions],
                [1, 0, 0, 1],
            )

    def test_symbol_table_looks_up_declarations_by_fqn_and_preserves_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.aidl"
            second = root / "b.aidl"
            first.write_text(
                "module example.catalog\nentity Pet {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.catalog\nvalue Pet {\n}\nentity Owner {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            matches = project.symbol_table.lookup_declarations("example.catalog.Pet")
            self.assertEqual(
                [
                    (match.document.source_path.name, match.declaration.kind)
                    for match in matches
                ],
                [("a.aidl", "entity"), ("b.aidl", "value")],
            )
            self.assertEqual(
                [
                    match.fully_qualified_name
                    for match in project.symbol_table.lookup_declarations(
                        "example.catalog.Owner"
                    )
                ],
                ["example.catalog.Owner"],
            )
            self.assertEqual(
                project.symbol_table.lookup_declarations("example.catalog.Missing"),
                (),
            )

    def test_operation_lookup_is_module_scoped_and_preserves_duplicate_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a-first.aidl").write_text(
                "module example.first\n"
                "query findPet() -> string {\n}\n"
                "mutation savePet() -> string {\n}\n",
                encoding="utf-8",
            )
            (root / "b-first.aidl").write_text(
                "module example.first\n"
                "workflow findPet() -> string {\n}\n",
                encoding="utf-8",
            )
            (root / "c-second.aidl").write_text(
                "module example.second\n"
                "query findPet() -> string {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            first_matches = project.symbol_table.lookup_operations(
                "example.first", "findPet"
            )
            self.assertEqual(
                [
                    (match.document.source_path.name, match.declaration.kind)
                    for match in first_matches
                ],
                [("a-first.aidl", "query"), ("b-first.aidl", "workflow")],
            )
            self.assertEqual(
                [
                    match.declaration.kind
                    for match in project.symbol_table.lookup_operations(
                        "example.second", "findPet"
                    )
                ],
                ["query"],
            )
            self.assertEqual(
                project.symbol_table.lookup_operations("example.second", "savePet"),
                (),
            )

    def test_operation_index_order_is_stable_and_excludes_non_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.aidl").write_text(
                "module example.ops\n"
                "task zeta() -> string {\n}\n"
                "entity NotAnOperation {\n}\n"
                "policy alpha() -> bool {\n}\n",
                encoding="utf-8",
            )
            (root / "b.aidl").write_text(
                "module example.ops\n"
                "saga beta() -> string {\n}\n"
                "query alpha() -> string {\n}\n",
                encoding="utf-8",
            )

            project = compiler_project.load_compiler_project([root])

            module_operations = project.symbol_table.operations_by_module["example.ops"]
            self.assertEqual(list(module_operations), ["zeta", "alpha", "beta"])
            self.assertEqual(
                [match.declaration.kind for match in module_operations["alpha"]],
                ["policy", "query"],
            )
            self.assertNotIn("NotAnOperation", module_operations)
            self.assertEqual(
                list(project.symbol_table.declarations_by_fqn),
                [
                    "example.ops.zeta",
                    "example.ops.NotAnOperation",
                    "example.ops.alpha",
                    "example.ops.beta",
                ],
            )


if __name__ == "__main__":
    unittest.main()
