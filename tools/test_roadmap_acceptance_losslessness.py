from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERIC_PREFIX = "Complete the work described for "


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _section(text: str, heading: str, level: int = 3) -> str:
    marker = "#" * level
    match = re.search(rf"^{marker}\s+{re.escape(heading)}\b[^\n]*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"missing source heading: {heading}")
    following = text[match.end():]
    next_heading = re.search(rf"^#{{2,{level}}}\s+", following, re.MULTILINE)
    return following[: next_heading.start() if next_heading else len(following)]


def _checkbox_contracts(section: str) -> list[str]:
    result: list[str] = []
    pattern = re.compile(r"^- \[[ xX]\]\s+\*\*P[0-2](?:/P[0-2])?\*\*\s+(.+)$", re.MULTILINE)
    for match in pattern.finditer(section):
        result.append(match.group(1).strip())
    return result


def _acceptance_line(section: str) -> str:
    match = re.search(r"^\*\*Acceptance:\*\*\s+(.+)$", section, re.MULTILINE)
    if match is None:
        raise AssertionError("missing package Acceptance line")
    return match.group(1).strip()


def _exit_contracts(text: str) -> list[str]:
    section = _section(text, "Python exit criteria", level=2)
    result: list[str] = []
    for line in section.splitlines():
        match = re.match(r"^- \*\*([^*]+):\*\*\s+(.+)$", line)
        if match:
            result.append(f"{match.group(1)}: {match.group(2)}")
    return result


class RoadmapAcceptanceLosslessnessTest(unittest.TestCase):
    def _packages(self, relative: str) -> dict[str, dict]:
        return {package["id"]: package for package in _load(relative)["packages"]}

    def assert_materialized(self, package: dict, expected: list[str]) -> None:
        self.assertTrue(expected, package["id"])
        self.assertEqual(expected, package["acceptance_criteria"], package["id"])
        self.assertFalse(
            any(item.startswith(GENERIC_PREFIX) for item in package["acceptance_criteria"]),
            package["id"],
        )

    def test_m10_5_phase_contracts_match_source(self) -> None:
        source = (ROOT / "backlog/m10-5-kotlin-compiler-migration.md").read_text(encoding="utf-8")
        packages = self._packages("roadmap/v1/milestones/m10.5.json")
        for package_id in [f"M10.5-{number:02d}" for number in range(1, 7)]:
            expected = _checkbox_contracts(_section(source, package_id))
            self.assert_materialized(packages[package_id], expected)
        self.assert_materialized(packages["M10.5-07"], _exit_contracts(source))

    def test_m11_section_contracts_match_source(self) -> None:
        source = (ROOT / "backlog/m11-compiler-service.md").read_text(encoding="utf-8")
        packages = self._packages("roadmap/v1/milestones/m11.json")
        for package_id in ["M11-04.1", "M11.5", "M11.6", "M11.7", "M11.8", "M11.9", "M11.10"]:
            expected = _checkbox_contracts(_section(source, package_id))
            self.assert_materialized(packages[package_id], expected)

    def test_m16_5_executor_acceptance_matches_source(self) -> None:
        source = (ROOT / "backlog/m16-5-language-surface-normalization.md").read_text(encoding="utf-8")
        packages = self._packages("roadmap/v1/milestones/m16.5.json")
        for number in range(1, 10):
            package_id = f"M16.5-E{number}"
            expected = [_acceptance_line(_section(source, f"E{number}"))]
            self.assert_materialized(packages[package_id], expected)

    def test_m16_5_completed_design_evidence_is_explicit(self) -> None:
        packages = self._packages("roadmap/v1/milestones/m16.5.json")
        evidence = {
            package_id: {item["ref"] for item in packages[package_id]["evidence"]}
            for package_id in ("M16.5-E1", "M16.5-E2")
        }
        self.assertIn("docs/m16-5-e1-design-decision.md", evidence["M16.5-E1"])
        self.assertIn("docs/m16-5-e2-compatibility-migration-contract.md", evidence["M16.5-E2"])


if __name__ == "__main__":
    unittest.main()
