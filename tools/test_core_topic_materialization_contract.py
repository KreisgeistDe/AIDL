from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir


ROOT = Path(__file__).resolve().parents[1]
BASE_SOURCE = (ROOT / "fixtures" / "valid" / "m4-minimal" / "app.aidl").read_text(encoding="utf-8")
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))


class CoreTopicMaterializationContractTests(unittest.TestCase):
    def _analysis(self, source: str):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        (root / "app.aidl").write_text(source, encoding="utf-8")
        analysis = load_compiler_analysis([root])
        self.addCleanup(directory.cleanup)
        return analysis

    def _topic_errors(self, source: str):
        analysis = self._analysis(source)
        return tuple(
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.severity == CompilerDiagnosticSeverity.ERROR
            and diagnostic.code.value == "AIDL-T005"
            and diagnostic.subject.kind == "topic"
        )

    @staticmethod
    def _topic(ir: dict) -> dict:
        return next(
            declaration
            for declaration in ir["declarations"]
            if declaration["kind"] == "topic" and declaration["name"] == "SnapshotItemEvents"
        )

    def _valid_ir(self, source: str = BASE_SOURCE) -> dict:
        analysis = self._analysis(source)
        errors = [
            diagnostic.to_json()
            for diagnostic in analysis.diagnostics
            if diagnostic.severity == CompilerDiagnosticSeverity.ERROR
        ]
        self.assertEqual([], errors)
        return build_canonical_ir(analysis)

    def test_explicit_topic_contract_is_deterministic_and_schema_valid(self) -> None:
        first = self._valid_ir()
        second = self._valid_ir()
        first_topic = self._topic(first)
        second_topic = self._topic(second)
        self.assertEqual(first_topic, second_topic)

        event = next(
            declaration
            for declaration in first["declarations"]
            if declaration["kind"] == "event" and declaration["name"] == "SnapshotItemCreated"
        )
        self.assertEqual([event["declarationId"]], first_topic["eventIds"])
        self.assertEqual("atLeastOnce", first_topic["delivery"])
        self.assertEqual("itemId", first_topic["partitionField"])
        self.assertEqual("perPartition", first_topic["ordering"])
        self.assertEqual(30 * 24 * 60 * 60 * 1000, first_topic["retentionMs"])
        self.assertEqual("backward", first_topic["compatibility"])
        self.assertEqual(8, first_topic["deadLetterAttempts"])

        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        self.assertEqual([], list(validator.iter_errors(first)))

    def test_all_required_topic_singletons_are_explicit(self) -> None:
        lines = {
            "events": "  events [SnapshotItemCreated]\n",
            "delivery": "  delivery atLeastOnce\n",
            "partition": "  partition by itemId\n",
            "ordering": "  ordering perPartition\n",
            "retention": "  retention 30d\n",
            "compatibility": "  compatibility backward\n",
            "deadLetter": "  deadLetter after 8 attempts\n",
        }
        for key, line in lines.items():
            with self.subTest(key=key):
                diagnostics = self._topic_errors(BASE_SOURCE.replace(line, "", 1))
                self.assertTrue(diagnostics)
                self.assertTrue(any("requires one explicit" in item.message for item in diagnostics))

    def test_repeated_singleton_is_rejected_before_ir(self) -> None:
        source = BASE_SOURCE.replace(
            "  ordering perPartition\n",
            "  ordering perPartition\n  ordering none\n",
            1,
        )
        diagnostics = self._topic_errors(source)
        self.assertTrue(any("singleton clause" in item.message for item in diagnostics))

    def test_event_references_resolve_uniquely_to_events(self) -> None:
        cases = {
            "unresolved": BASE_SOURCE.replace("events [SnapshotItemCreated]", "events [MissingEvent]", 1),
            "wrong_kind": BASE_SOURCE.replace("events [SnapshotItemCreated]", "events [SnapshotItem]", 1),
            "duplicate": BASE_SOURCE.replace(
                "events [SnapshotItemCreated]",
                "events [SnapshotItemCreated, SnapshotItemCreated]",
                1,
            ),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                diagnostics = self._topic_errors(source)
                self.assertTrue(diagnostics)

    def test_only_closed_delivery_ordering_and_compatibility_values_reach_ir(self) -> None:
        cases = {
            "delivery": BASE_SOURCE.replace("delivery atLeastOnce", "delivery atMostOnce", 1),
            "ordering": BASE_SOURCE.replace("ordering perPartition", "ordering global", 1),
            "compatibility": BASE_SOURCE.replace("compatibility backward", "compatibility rolling", 1),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                diagnostics = self._topic_errors(source)
                self.assertTrue(diagnostics)
                self.assertTrue(any("outside the closed Core Topic IR contract" in item.message for item in diagnostics))

    def test_partition_must_be_losslessly_projectable_symbol_path(self) -> None:
        source = BASE_SOURCE.replace("partition by itemId", "partition by itemId + 1", 1)
        diagnostics = self._topic_errors(source)
        self.assertTrue(any("not losslessly projectable as partitionField" in item.message for item in diagnostics))

    def test_retention_and_dead_letter_attempts_must_be_positive(self) -> None:
        cases = {
            "retention": BASE_SOURCE.replace("retention 30d", "retention 0d", 1),
            "dead_letter": BASE_SOURCE.replace("deadLetter after 8 attempts", "deadLetter after 0 attempts", 1),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                diagnostics = self._topic_errors(source)
                self.assertTrue(diagnostics)

    def test_supported_nondefault_values_are_preserved_exactly(self) -> None:
        source = (
            BASE_SOURCE
            .replace("partition by itemId", "partition by payload.itemId", 1)
            .replace("ordering perPartition", "ordering none", 1)
            .replace("retention 30d", "retention 2h", 1)
            .replace("compatibility backward", "compatibility full", 1)
            .replace("deadLetter after 8 attempts", "deadLetter after 3 attempts", 1)
        )
        topic = self._topic(self._valid_ir(source))
        # The parser owns whitespace normalization around member access; the
        # materialization boundary proves this remains a simple symbol path.
        self.assertEqual("payload . itemId", topic["partitionField"])
        self.assertEqual("none", topic["ordering"])
        self.assertEqual(2 * 60 * 60 * 1000, topic["retentionMs"])
        self.assertEqual("full", topic["compatibility"])
        self.assertEqual(3, topic["deadLetterAttempts"])


if __name__ == "__main__":
    unittest.main()
