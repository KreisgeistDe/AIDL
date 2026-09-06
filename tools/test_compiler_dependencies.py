from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_dependencies import (
    MAX_DIRECT_DEPENDENCIES,
    MAX_TRANSITIVE_DEPENDENCIES,
    collect_project_dependencies,
)
from tools.compiler_diagnostics import load_compiler_analysis
from tools.test_aidl_ir import _MINIMAL_PROJECT


class CompilerDependenciesTest(unittest.TestCase):
    def _collect(self, project: str, fqn: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(project, encoding="utf-8")
            analysis = load_compiler_analysis([source])
            return collect_project_dependencies(analysis, fqn)

    def test_query_dependencies_come_only_from_canonical_ir_references(self) -> None:
        result = self._collect(_MINIMAL_PROJECT, "demo.getPet")

        self.assertEqual("resolved", result.status)
        self.assertIsNotNone(result.declaration)
        self.assertEqual("demo.getPet@1", result.declaration.declaration_id)
        self.assertEqual(
            [("demo.Pet", "entity", "demo.Pet@1")],
            [
                (item.fully_qualified_name, item.kind, item.declaration_id)
                for item in result.dependencies
            ],
        )
        self.assertEqual(1, result.direct_total)
        self.assertFalse(result.direct_truncated)

    def test_transitive_dependencies_are_reachability_over_direct_ir_edges(self) -> None:
        project = _MINIMAL_PROJECT + (
            "\nexport value C { id: uuid required }\n"
            "export value B { c: C required }\n"
            "export value A { b: B required }\n"
        )
        result = self._collect(project, "demo.A")

        self.assertEqual(["demo.B"], [item.fully_qualified_name for item in result.dependencies])
        self.assertEqual(
            ["demo.C"],
            [item.fully_qualified_name for item in result.transitive_dependencies],
        )
        self.assertEqual(1, result.direct_total)
        self.assertEqual(1, result.transitive_total)
        self.assertFalse(result.direct_truncated)
        self.assertFalse(result.transitive_truncated)

    def test_cycle_is_safe_and_never_returns_target(self) -> None:
        project = _MINIMAL_PROJECT + (
            "\nexport value A { b: B required }\n"
            "export value B { c: C required }\n"
            "export value C { a: A required }\n"
        )
        result = self._collect(project, "demo.A")

        direct = [item.fully_qualified_name for item in result.dependencies]
        transitive = [item.fully_qualified_name for item in result.transitive_dependencies]
        self.assertEqual(["demo.B"], direct)
        self.assertEqual(["demo.C"], transitive)
        self.assertNotIn("demo.A", direct + transitive)

    def test_dependencies_are_stably_sorted_deduplicated_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            analysis = load_compiler_analysis([source])
            first = collect_project_dependencies(analysis, "demo.DemoSystem").to_json()
            second = collect_project_dependencies(analysis, "demo.DemoSystem").to_json()

        self.assertEqual(first, second)
        dependencies = first["dependencies"]
        fqns = [item["fullyQualifiedName"] for item in dependencies]
        self.assertEqual(sorted(set(fqns)), fqns)
        transitive = first["transitiveDependencies"]
        transitive_fqns = [item["fullyQualifiedName"] for item in transitive]
        self.assertEqual(sorted(set(transitive_fqns)), transitive_fqns)
        self.assertNotIn("demo.DemoSystem", fqns + transitive_fqns)
        self.assertEqual(
            {"directDependencies": len(dependencies), "transitiveDependencies": len(transitive)},
            first["totals"],
        )
        self.assertEqual(
            {"directDependencies": False, "transitiveDependencies": False},
            first["truncated"],
        )

    def test_direct_and_transitive_outputs_are_bounded_with_full_totals(self) -> None:
        leaf_count = MAX_DIRECT_DEPENDENCIES + 2
        leaf_declarations = "".join(
            f"export value Leaf{index:03d} {{ id: uuid required }}\n"
            for index in range(leaf_count)
        )
        hub_fields = "".join(
            f"  leaf{index:03d}: Leaf{index:03d} required\n"
            for index in range(leaf_count)
        )
        root_fields = hub_fields
        project = (
            _MINIMAL_PROJECT
            + "\n"
            + leaf_declarations
            + "export value Hub {\n"
            + hub_fields
            + "}\n"
            + "export value Root {\n"
            + "  hub: Hub required\n"
            + root_fields
            + "}\n"
        )
        result = self._collect(project, "demo.Root")

        self.assertEqual(leaf_count + 1, result.direct_total)
        self.assertEqual(MAX_DIRECT_DEPENDENCIES, len(result.dependencies))
        self.assertTrue(result.direct_truncated)
        self.assertEqual(0, result.transitive_total)
        self.assertFalse(result.transitive_truncated)

        transitive_project = (
            _MINIMAL_PROJECT
            + "\n"
            + leaf_declarations
            + "export value Hub {\n"
            + hub_fields
            + "}\n"
            + "export value Root { hub: Hub required }\n"
        )
        transitive_result = self._collect(transitive_project, "demo.Root")
        self.assertEqual(1, transitive_result.direct_total)
        self.assertEqual(leaf_count, transitive_result.transitive_total)
        self.assertEqual(
            MAX_TRANSITIVE_DEPENDENCIES,
            len(transitive_result.transitive_dependencies),
        )
        self.assertTrue(transitive_result.transitive_truncated)

    def test_invalid_unknown_and_ambiguous_fqns_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            analysis = load_compiler_analysis([source])
            invalid = collect_project_dependencies(analysis, "not a fqn")
            unknown = collect_project_dependencies(analysis, "demo.Missing")

            duplicate_a = root / "a.aidl"
            duplicate_b = root / "b.aidl"
            duplicate_a.write_text("module dup\nexport enum Same { a }\n", encoding="utf-8")
            duplicate_b.write_text("module dup\nexport enum Same { b }\n", encoding="utf-8")
            duplicate_analysis = load_compiler_analysis([duplicate_a, duplicate_b])
            ambiguous = collect_project_dependencies(duplicate_analysis, "dup.Same")

        self.assertEqual("invalid", invalid.status)
        self.assertEqual("unknown", unknown.status)
        self.assertEqual("ambiguous", ambiguous.status)
        self.assertEqual(2, ambiguous.match_count)


if __name__ == "__main__":
    unittest.main()
