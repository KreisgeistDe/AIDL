from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class BoundedCollectionQueryDiagnosticsTest(unittest.TestCase):
    def test_page_return_with_page_bound_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query ListPets(page: PageInput) -> Page<Pet> {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true)\n"
                "         .sort(createdAt desc)\n"
                "         .page(page)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [d for d in analysis.diagnostics if d.code == "AIDL-DIST413"],
                [],
            )

    def test_direct_list_return_with_limit_bound_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query RecentPets() -> [Pet] {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true).limit(25)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [d for d in analysis.diagnostics if d.code == "AIDL-DIST413"],
                [],
            )

    def test_unbounded_page_return_is_rejected_at_read_clause(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query ListPets() -> Page<Pet> {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [
                d for d in analysis.diagnostics if d.code == "AIDL-DIST413"
            ]

            self.assertEqual(len(diagnostics), 1)
            self.assertEqual(
                diagnostics[0].message,
                "collection query 'example.queries.ListPets' returning 'Page<Pet>' must declare an explicit page or limit bound in its read path",
            )
            self.assertEqual((diagnostics[0].location.line, diagnostics[0].location.column), (4, 3))
            self.assertEqual(diagnostics[0].phase, "policy")
            self.assertEqual(diagnostics[0].severity, "error")

    def test_unbounded_direct_list_return_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query RecentPets() -> [Pet] {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [
                d for d in analysis.diagnostics if d.code == "AIDL-DIST413"
            ]

            self.assertEqual(len(diagnostics), 1)
            self.assertIn("returning '[Pet]'", diagnostics[0].message)
            self.assertEqual((diagnostics[0].location.line, diagnostics[0].location.column), (4, 3))

    def test_single_result_and_named_return_types_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query GetPet(id: PetId) -> Pet? {\n"
                "  auth: private\n"
                "  read: Pet.byId(id)\n"
                "}\n"
                "query NamedCollection() -> PetList {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [d for d in analysis.diagnostics if d.code == "AIDL-DIST413"],
                [],
            )

    def test_bound_must_be_in_retained_read_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query ListPets() -> [Pet] {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true)\n"
                "  cache: Pet.limit(10)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                len([d for d in analysis.diagnostics if d.code == "AIDL-DIST413"]),
                1,
            )

    def test_missing_read_path_anchors_to_query_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query ListPets() -> [Pet] {\n"
                "  auth: private\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                d for d in analysis.diagnostics if d.code == "AIDL-DIST413"
            )

            self.assertEqual((diagnostic.location.line, diagnostic.location.column), (2, 1))

    def test_diagnostic_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "query First() -> Page<Item> {\n"
                "  auth: private\n"
                "  read: Item.all()\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "query Second() -> [Item] {\n"
                "  auth: private\n"
                "  read: Item.all()\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])

            def bounded(analysis: compiler_diagnostics.CompilerAnalysis):
                return tuple(d for d in analysis.diagnostics if d.code == "AIDL-DIST413")

            first_diagnostics = bounded(first_analysis)
            second_diagnostics = bounded(second_analysis)
            self.assertEqual(
                [
                    (d.source_path.name, d.location.line, d.location.column, d.message)
                    for d in first_diagnostics
                ],
                [
                    (d.source_path.name, d.location.line, d.location.column, d.message)
                    for d in second_diagnostics
                ],
            )
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(first_diagnostics)
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(second_diagnostics)
            self.assertEqual(first_json, second_json)
            payload = json.loads(first_json)
            self.assertEqual([item["code"] for item in payload], ["AIDL-DIST413", "AIDL-DIST413"])
            self.assertEqual([Path(item["location"]["file"]).name for item in payload], ["a-first.aidl", "b-second.aidl"])


if __name__ == "__main__":
    unittest.main()
