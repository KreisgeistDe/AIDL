from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class TransactionOutboxDiagnosticsTest(unittest.TestCase):
    def test_mutation_transaction_emit_via_outbox_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    emit: OrderChanged() to OrderEvents via outbox\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_consumer_nested_emit_via_outbox_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [readCommitted]\n"
                "}\n"
                "consumer ApplyOrder {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  transaction on OrderDb isolation readCommitted {\n"
                "    when true {\n"
                "      emit: OrderApplied() to OrderEvents via outbox\n"
                "    }\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  runs [consumer ApplyOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_transaction_emit_requires_via_outbox_with_source_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    emit: OrderChanged() to OrderEvents\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(
                diagnostic.code,
                compiler_diagnostics.CompilerDiagnosticCode.TRANSACTION_OUTBOX,
            )
            self.assertEqual(diagnostic.code, "AIDL-DIST408")
            self.assertEqual(diagnostic.phase, "policy")
            self.assertEqual(
                diagnostic.severity,
                compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            )
            self.assertEqual(
                diagnostic.message,
                "emit in transaction of 'example.orders.ChangeOrder' must use 'via outbox'",
            )
            self.assertEqual(diagnostic.source_path, source)
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (11, 5),
            )

    def test_nested_transaction_emit_requires_via_outbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    when true {\n"
                "      emit: OrderChanged() to OrderEvents\n"
                "    }\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(diagnostic.code, "AIDL-DIST408")
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (12, 7),
            )

    def test_emit_outside_transaction_does_not_add_m2_08_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "query.aidl"
            source.write_text(
                "module example.orders\n"
                "query ReadOrder {\n"
                "  emit: OrderRead() to OrderEvents\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [diagnostic.code.value for diagnostic in analysis.diagnostics],
                ["AIDL-DIST403"],
            )

    def test_outbox_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "resource FirstDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation FirstMutation {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  transaction on FirstDb isolation serializable {\n"
                "    emit: FirstEvent() to FirstEvents\n"
                "  }\n"
                "}\n"
                "service FirstService {\n"
                "  uses [FirstDb]\n"
                "  exposes [mutation FirstMutation]\n"
                "}\n"
                "error Failure {\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "resource SecondDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "consumer SecondConsumer {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  transaction on SecondDb isolation serializable {\n"
                "    when true {\n"
                "      emit: SecondEvent() to SecondEvents\n"
                "    }\n"
                "  }\n"
                "}\n"
                "service SecondService {\n"
                "  uses [SecondDb]\n"
                "  runs [consumer SecondConsumer]\n"
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
                    "AIDL-DIST408",
                    "emit in transaction of 'example.first.FirstMutation' must use 'via outbox'",
                    "a-first.aidl",
                    11,
                    5,
                ),
                (
                    "AIDL-DIST408",
                    "emit in transaction of 'example.second.SecondConsumer' must use 'via outbox'",
                    "b-second.aidl",
                    9,
                    7,
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
                ["AIDL-DIST408", "AIDL-DIST408"],
            )


if __name__ == "__main__":
    unittest.main()
