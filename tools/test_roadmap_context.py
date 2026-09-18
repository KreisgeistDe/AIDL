from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import roadmap_context

ROOT = Path(__file__).resolve().parents[1]


class RoadmapContextTest(unittest.TestCase):
    def temp_repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "roadmap", root / "roadmap")
        shutil.copytree(ROOT / "backlog", root / "backlog")
        shutil.copy2(ROOT / "TODO.md", root / "TODO.md")
        index = json.loads((root / "roadmap/v1/index.json").read_text())
        refs = {"spec/roadmap-v1.schema.json"}
        for entry in index["milestones"]:
            milestone = json.loads((root / entry["path"]).read_text())
            source = milestone.get("source")
            if isinstance(source, dict) and source.get("kind") in {"path", "test", "schema"}:
                refs.add(source["ref"])
            projection = milestone.get("status_projection")
            if isinstance(projection, dict):
                refs.add(projection["path"])
            for package in milestone["packages"]:
                for link in [*package["evidence"], *package["references"]]:
                    if link["kind"] in {"path", "test", "schema"}:
                        refs.add(link["ref"])
        for ref in sorted(refs):
            source = ROOT / ref
            target = root / ref
            if target.exists() or not source.is_file():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return td, root

    def test_ready_package_context(self):
        value = roadmap_context.context_data("M10.5-04", ROOT)
        self.assertEqual("aidl.roadmap-context/v1", value["schema_version"])
        self.assertEqual("ready", value["selected"]["state"])
        self.assertEqual("M10.5-04", value["next_candidates"]["items"][0]["id"])
        self.assertGreater(value["remaining_acceptance_criteria"]["total"], 0)

    def test_blocked_package_reports_transitive_blockers_and_ready_candidate(self):
        value = roadmap_context.context_data("M11-04.1", ROOT)
        self.assertEqual("blocked", value["selected"]["state"])
        blocker_ids = [row["id"] for row in value["transitive_blockers"]["items"]]
        self.assertIn("M10.5-06", blocker_ids)
        self.assertTrue(value["next_candidates"]["items"])
        self.assertTrue(all(row["state"] in {"ready", "in_progress"} for row in value["next_candidates"]["items"]))

    def test_historical_supersession_is_copied_without_new_authority(self):
        value = roadmap_context.context_data("M16.5-E3", ROOT)
        self.assertEqual("terminal", value["selected"]["state"])
        authority = value["selected"]["authority"]
        self.assertEqual("historical_nonblocking", authority["authority_status"])
        self.assertEqual("spec/core-authority-transition-v1.json", authority["superseded_by_authority"][0]["ref"])
        self.assertEqual([], authority["supersedes"])
        self.assertEqual([], authority["superseded_by"])
        self.assertEqual([], value["remaining_acceptance_criteria"]["items"])

    def test_terminal_complete_package_has_no_remaining_acceptance(self):
        value = roadmap_context.context_data("M9-06", ROOT)
        self.assertEqual("terminal", value["selected"]["state"])
        self.assertEqual(0, value["remaining_acceptance_criteria"]["total"])
        self.assertEqual(0, value["next_candidates"]["total"])

    def test_milestone_context_is_bounded_and_deterministic(self):
        first = roadmap_context.context_data("M16.5", ROOT, limit=2)
        second = roadmap_context.context_data("M16.5", ROOT, limit=2)
        self.assertEqual(first, second)
        self.assertEqual("milestone", first["selected"]["kind"])
        self.assertEqual("historical_nonblocking", first["selected"]["authority"]["authority_status"])
        for key in ("direct_dependencies", "transitive_blockers", "next_candidates", "remaining_acceptance_criteria", "evidence", "references"):
            self.assertLessEqual(len(first[key]["items"]), 2)
        self.assertEqual(2, first["limits"]["requested"])

    def test_unknown_selector_fails_closed(self):
        with self.assertRaises(KeyError):
            roadmap_context.context_data("M404-01", ROOT)

    def test_invalid_graph_fails_closed(self):
        td, root = self.temp_repo()
        try:
            path = root / "roadmap/v1/milestones/m10.5.json"
            data = json.loads(path.read_text())
            data["packages"][3]["depends_on"] = ["M404-01"]
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                roadmap_context.context_data("M10.5-04", root)
        finally:
            td.cleanup()

    def test_authoritative_links_are_not_invented(self):
        value = roadmap_context.context_data("M10.5-04", ROOT)
        authority = value["selected"]["authority"]
        self.assertIsNone(authority["authority_status"])
        self.assertEqual([], authority["supersedes"])
        self.assertEqual([], authority["superseded_by"])
        self.assertEqual([], authority["superseded_by_authority"])


if __name__ == "__main__":
    unittest.main()
