from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class ConsumerIdempotencyDiagnosticsTest(unittest.TestCase):
    def test_pure_consumer_without_idempotency_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer ObserveOrder {\n"
                "  retry: exponential (attempts:3)\n"
                "  when event.active {\n"
                "    require event.id != null\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_effectful_consumer_with_one_idempotency_contract_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer StartReview {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  start: workflow ReviewOrder(event.id)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_call_effect_requires_idempotency_with_consumer_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  call: refreshOrder(event.id)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(
                diagnostic.code,
                compiler_diagnostics.CompilerDiagnosticCode.CONSUMER_IDEMPOTENCY,
            )
            self.assertEqual(diagnostic.code, "AIDL-DIST411")
            self.assertEqual(diagnostic.phase, "policy")
            self.assertEqual(
                diagnostic.severity,
                compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            )
            self.assertEqual(
                diagnostic.message,
                "effectful consumer 'example.orders.ApplyOrder' must declare exactly one "
                "'idempotency' clause; found 0",
            )
            self.assertEqual(diagnostic.source_path, source)
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (2, 1),
            )

    def test_transaction_effect_requires_idempotency_without_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  transaction on MissingDb isolation serializable {\n"
                "    require event.id != null\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [diagnostic.code.value for diagnostic in analysis.diagnostics],
                ["AIDL-DIST411"],
            )
            self.assertEqual(
                (analysis.diagnostics[0].location.line, analysis.diagnostics[0].location.column),
                (2, 1),
            )

    def test_nested_start_effect_requires_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  when event.active {\n"
                "    start: workflow ApplyWorkflow(event.id)\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [diagnostic.code.value for diagnostic in analysis.diagnostics],
                ["AIDL-DIST411"],
            )

    def test_effectful_consumer_rejects_duplicate_top_level_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  idempotency: event.eventId retain 7d\n"
                "  call: refreshOrder(event.id)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(diagnostic.code, "AIDL-DIST411")
            self.assertEqual(
                diagnostic.message,
                "effectful consumer 'example.orders.ApplyOrder' must declare exactly one "
                "'idempotency' clause; found 2",
            )
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (4, 3),
            )

    def test_existing_transaction_outbox_rule_remains_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  transaction on MissingDb isolation serializable {\n"
                "    emit: OrderApplied() to OrderEvents\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [diagnostic.code.value for diagnostic in analysis.diagnostics],
                ["AIDL-DIST408"],
            )
            self.assertEqual(
                (analysis.diagnostics[0].location.line, analysis.diagnostics[0].location.column),
                (5, 5),
            )

    def test_consumer_idempotency_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "consumer FirstConsumer {\n"
                "  call: doFirst(event.id)\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "consumer SecondConsumer {\n"
                "  when event.active {\n"
                "    start: workflow SecondWorkflow(event.id)\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis(
                [second, first]
            )

            def snapshot(analysis: compiler_diagnostics.CompilerAnalysis):
                return [
                    (
                        diagnostic.code.value,
                        diagnostic.message,
                        diagnostic.source_path.name,
                        diagnostic.location.line,
                        diagnostic.location.column,
                    )
                    for diagnostic in analysis.diagnostics
                ]

            expected = [
                (
                    "AIDL-DIST411",
                    "effectful consumer 'example.first.FirstConsumer' must declare exactly one "
                    "'idempotency' clause; found 0",
                    "a-first.aidl",
                    2,
                    1,
                ),
                (
                    "AIDL-DIST411",
                    "effectful consumer 'example.second.SecondConsumer' must declare exactly one "
                    "'idempotency' clause; found 0",
                    "b-second.aidl",
                    2,
                    1,
                ),
            ]
            self.assertEqual(snapshot(first_analysis), expected)
            self.assertEqual(snapshot(second_analysis), expected)

            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                first_analysis.diagnostics
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                second_analysis.diagnostics
            )
            self.assertEqual(first_json, second_json)
            self.assertEqual(
                [item["code"] for item in json.loads(first_json)],
                ["AIDL-DIST411", "AIDL-DIST411"],
            )


if __name__ == "__main__":
    unittest.main()
