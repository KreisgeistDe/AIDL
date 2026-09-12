from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import roadmap

ROOT = Path(__file__).resolve().parents[1]
COPIED = (
    "spec/roadmap-v1.schema.json",
    "roadmap/v1/index.json",
    "roadmap/v1/milestones/m10.json",
    "roadmap/v1/milestones/m10.1.json",
    "TODO.md",
    "backlog/m9-m10-release-conformance.md",
    "backlog/m10-1-language-freeze.md",
    "spec/conformance-manifest.json",
    "docs/m10-1-language-surface-freeze.md",
    "docs/m10-1-closure-certification.md",
    "spec/language-surface-v1.json",
    "tools/compiler_language_surface_certification.py",
    "tools/test_m10_1_language_surface_certification.py",
)


class RoadmapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in COPIED:
            source = ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def load(self, relative: str) -> dict:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def write(self, relative: str, value: dict) -> None:
        (self.root / relative).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def codes(self) -> list[str]:
        return [item["code"] for item in roadmap.validate_repository(self.root)]

    def test_valid_data_and_queries(self) -> None:
        self.assertEqual(roadmap.validate_repository(self.root), [])
        summary = roadmap.summary_data(self.root)
        self.assertEqual(summary["milestones"], 2)
        self.assertEqual(summary["packages"], 17)
        self.assertEqual(summary["status_counts"]["complete"], 17)
        self.assertEqual(summary["status_counts"]["open"], 0)
        self.assertEqual(summary["blocked"], 0)
        self.assertIsNone(roadmap.next_data(self.root))
        _, _, packages = roadmap.load_authority(self.root)
        self.assertEqual(roadmap.blocker_ids(packages, "M10.1-10", False), [])
        self.assertEqual(roadmap.blocker_ids(packages, "M10.1-10", True), [])
        completed = roadmap.completed_data(self.root)
        self.assertIn("M10", completed["complete_milestones"])
        self.assertIn("M10.1", completed["complete_milestones"])

    def test_terminal_dispositions_satisfy_dependencies(self) -> None:
        data = self.load("roadmap/v1/milestones/m10.1.json")
        data["packages"][5]["status"] = "not_applicable"
        data["packages"][5]["disposition_reason"] = "Explicitly not applicable for this compatibility profile."
        data["packages"][6]["status"] = "excluded"
        data["packages"][6]["disposition_reason"] = "Explicitly excluded from the frozen v1 surface."
        packages = {package["id"]: package for package in data["packages"]}
        self.assertFalse(roadmap.is_blocked(data["packages"][7], packages))

    def test_schema_violation(self) -> None:
        data = self.load("roadmap/v1/milestones/m10.json")
        data["packages"][0]["status"] = "done"
        self.write("roadmap/v1/milestones/m10.json", data)
        self.assertIn("ROADMAP-E001", self.codes())

    def test_duplicate_id_and_order(self) -> None:
        data = self.load("roadmap/v1/milestones/m10.json")
        data["packages"][1]["id"] = data["packages"][0]["id"]
        data["packages"][1]["order"] = data["packages"][0]["order"]
        self.write("roadmap/v1/milestones/m10.json", data)
        self.assertIn("ROADMAP-E002", self.codes())

    def test_unknown_and_self_dependency(self) -> None:
        data = self.load("roadmap/v1/milestones/m10.1.json")
        data["packages"][5]["depends_on"] = ["M10.1-99"]
        self.write("roadmap/v1/milestones/m10.1.json", data)
        self.assertIn("ROADMAP-E003", self.codes())
        data["packages"][5]["depends_on"] = ["M10.1-06"]
        self.write("roadmap/v1/milestones/m10.1.json", data)
        self.assertIn("ROADMAP-E004", self.codes())

    def test_cycle(self) -> None:
        data = self.load("roadmap/v1/milestones/m10.1.json")
        data["packages"][0]["depends_on"] = ["M10.1-02"]
        self.write("roadmap/v1/milestones/m10.1.json", data)
        self.assertIn("ROADMAP-E005", self.codes())

    def test_index_file_mismatch(self) -> None:
        data = self.load("roadmap/v1/milestones/m10.json")
        data["title"] = "Drifted"
        self.write("roadmap/v1/milestones/m10.json", data)
        self.assertIn("ROADMAP-E007", self.codes())

    def test_invalid_evidence_path(self) -> None:
        data = self.load("roadmap/v1/milestones/m10.json")
        data["packages"][0]["evidence"] = [{"kind": "path", "ref": "../outside"}]
        self.write("roadmap/v1/milestones/m10.json", data)
        self.assertIn("ROADMAP-E006", self.codes())

    def test_markdown_json_drift(self) -> None:
        path = self.root / "TODO.md"
        path.write_text(path.read_text(encoding="utf-8").replace("- [x] **M10.1-09", "- [ ] **M10.1-09"), encoding="utf-8")
        self.assertIn("ROADMAP-E008", self.codes())

    def test_migration_scope_violation(self) -> None:
        index = self.load("roadmap/v1/index.json")
        index["migration"]["pending_milestones"].append("M10")
        self.write("roadmap/v1/index.json", index)
        self.assertIn("ROADMAP-E009", self.codes())

    def test_machine_output_is_byte_stable(self) -> None:
        first = json.dumps(roadmap.summary_data(self.root), sort_keys=True, separators=(",", ":"))
        second = json.dumps(roadmap.summary_data(self.root), sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
