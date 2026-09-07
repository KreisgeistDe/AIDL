from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import aidl_parser  # noqa: E402


class SourceDiscoveryTest(unittest.TestCase):
    def test_only_aidl_sources_are_recursive_sorted_and_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "z"
            nested.mkdir()
            nested_aidl = nested / "b.aidl"
            aidl = root / "a.aidl"
            legacy = root / "legacy.dsl"
            ignored = root / "ignored.txt"
            nested_aidl.write_text("module example.z\n", encoding="utf-8")
            aidl.write_text("module example.a\n", encoding="utf-8")
            legacy.write_text("module legacy\n", encoding="utf-8")
            ignored.write_text("module ignored\n", encoding="utf-8")

            discovered = aidl_parser.iter_aidl_files([root, nested_aidl])

            self.assertEqual(discovered, [aidl, nested_aidl])

    def test_non_aidl_explicit_source_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "single.dsl"
            source.write_text("module example.single\n", encoding="utf-8")

            self.assertEqual(aidl_parser.iter_aidl_files([source]), [])

    def test_explicit_aidl_source_file_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "single.aidl"
            source.write_text("module example.single\n", encoding="utf-8")

            self.assertEqual(aidl_parser.iter_aidl_files([source]), [source])

    def test_cli_emits_one_document_per_discovered_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "nested"
            nested.mkdir()
            first = root / "a.aidl"
            second = nested / "b.aidl"
            legacy = root / "legacy.dsl"
            first.write_text("module example.a\n", encoding="utf-8")
            second.write_text("module example.b\n", encoding="utf-8")
            legacy.write_text("module legacy\n", encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "aidl_parser.py"), str(root), str(second)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)

            self.assertEqual([doc["path"] for doc in payload["files"]], [str(first), str(second)])
            self.assertEqual(len(payload["files"]), 2)


class ContextualKeywordRegressionTest(unittest.TestCase):
    def test_keyword_tokens_remain_names_in_contextual_name_positions_deterministically(self) -> None:
        source = (
            "module example.query\n"
            "import example.entity.value\n"
            "entity value {\n"
            "}\n"
        )

        first_program, first_diagnostics, first_tokens = aidl_parser.parse_text(source)
        second_program, second_diagnostics, second_tokens = aidl_parser.parse_text(source)

        self.assertEqual(first_diagnostics, [])
        self.assertEqual(second_diagnostics, [])
        self.assertEqual(
            [(child.kind, child.name) for child in first_program.children],
            [
                ("module", "example.query"),
                ("import", "example.entity.value"),
                ("entity", "value"),
            ],
        )
        self.assertEqual(first_program.to_json(), second_program.to_json())
        self.assertEqual(
            [token.to_json() for token in first_tokens],
            [token.to_json() for token in second_tokens],
        )
        self.assertEqual(
            [
                (token.value, token.kind)
                for token in first_tokens
                if token.value in {"query", "entity", "value"}
            ],
            [
                ("query", "KEYWORD"),
                ("entity", "KEYWORD"),
                ("value", "KEYWORD"),
                ("entity", "KEYWORD"),
                ("value", "KEYWORD"),
            ],
        )


class EnumParserStateTest(unittest.TestCase):
    def test_enum_cases_preserve_assignment_and_malformed_source_state(self) -> None:
        source = """module example.enums
export enum State {
  Draft,
  Published = "published",
  Broken = 7
}
"""
        program, diagnostics, _ = aidl_parser.parse_text(source)

        self.assertEqual([], diagnostics)
        enum = next(child for child in program.children if child.kind == "enum")
        self.assertEqual(["Draft", "Published", "Broken"], enum.attrs["cases"])
        self.assertEqual(
            [
                {"raw": "Draft", "name": "Draft", "assignedValue": None, "malformed": False},
                {"raw": 'Published = "published"', "name": "Published", "assignedValue": '"published"', "malformed": False},
                {"raw": "Broken = 7", "name": "Broken", "malformed": True},
            ],
            enum.attrs["enumCases"],
        )

    def test_enum_trailing_comma_is_retained_as_malformed_case_state(self) -> None:
        program, diagnostics, _ = aidl_parser.parse_text("module example.enums\nenum State { Draft, }\n")
        self.assertEqual([], diagnostics)
        enum = next(child for child in program.children if child.kind == "enum")
        self.assertEqual(
            [
                {"raw": "Draft", "name": "Draft", "assignedValue": None, "malformed": False},
                {"raw": ",", "malformed": True},
            ],
            enum.attrs["enumCases"],
        )


if __name__ == "__main__":
    unittest.main()
