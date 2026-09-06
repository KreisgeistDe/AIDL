from __future__ import annotations

import copy
import unittest

from tools.conformance_docs import (
    CORE_MARKER,
    SURFACE_MARKER,
    generated_block,
    render_core_supported_table,
    render_surface_table,
    replace_generated_block,
    validate_documentation,
)
from tools.conformance_manifest import ROOT, core_supported_ids, load_core_fixture_matrix, load_core_matrix, load_manifest


class ConformanceDocumentationTests(unittest.TestCase):
    def test_repository_generated_coverage_is_current(self) -> None:
        self.assertEqual([], validate_documentation(ROOT))

    def test_surface_table_is_derived_from_manifest_order_and_statements(self) -> None:
        manifest = load_manifest(ROOT)
        table = render_surface_table(manifest)
        rows = [line for line in table.splitlines() if line.startswith("| `")]
        self.assertEqual(len(manifest["surfaces"]), len(rows))
        for surface, row in zip(manifest["surfaces"], rows, strict=True):
            self.assertIn(f"`{surface['id']}`", row)
            self.assertIn(f"| {surface['status']} |", row)
            self.assertIn(surface["supportStatement"], row)

    def test_core_table_is_exactly_the_core_supported_set(self) -> None:
        core = load_core_matrix(ROOT)
        fixture = load_core_fixture_matrix(ROOT)
        table = render_core_supported_table(core, fixture)
        rows = [line for line in table.splitlines() if line.startswith("| `")]
        self.assertEqual(core_supported_ids(core), [row.split("`")[1] for row in rows])

    def test_core_fixture_drift_is_rejected_before_rendering(self) -> None:
        core = load_core_matrix(ROOT)
        fixture = copy.deepcopy(load_core_fixture_matrix(ROOT))
        fixture["featureIds"] = fixture["featureIds"][:-1]
        with self.assertRaisesRegex(ValueError, "Core fixture featureIds drift"):
            render_core_supported_table(core, fixture)

    def test_marker_replacement_is_deterministic_and_rejects_missing_markers(self) -> None:
        original = f"before\n{generated_block(SURFACE_MARKER, 'old')}\nafter\n"
        expected = f"before\n{generated_block(SURFACE_MARKER, 'new')}\nafter\n"
        self.assertEqual(expected, replace_generated_block(original, SURFACE_MARKER, "new"))
        with self.assertRaisesRegex(ValueError, "missing generated documentation markers"):
            replace_generated_block("manual table only", CORE_MARKER, "new")

    def test_rendering_does_not_mutate_manifest_data(self) -> None:
        manifest = load_manifest(ROOT)
        candidate = copy.deepcopy(manifest)
        render_surface_table(candidate)
        self.assertEqual(manifest, candidate)


if __name__ == "__main__":
    unittest.main()
