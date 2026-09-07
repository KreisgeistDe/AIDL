from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir


_VALID_SOURCE = """module example.orders

app OrdersApp {
  profile core version 1
  system OrdersSystem
  defaultDeployment local
}

event OrderApplied version 1 {
  eventId: uuid required
}

topic OrderEvents {
  events [OrderApplied]
  delivery atLeastOnce
  partition by eventId
  ordering perPartition
  retention 30d
  compatibility backward
  deadLetter after 8 attempts
}

consumer ApplyOrder on OrderApplied from OrderEvents {
  service OrdersService
  idempotency: event.eventId retain 7d
  retry: none
}

service OrdersService {
  uses [OrderEvents]
  runs [consumer ApplyOrder]
}

system OrdersSystem {
  services [OrdersService]
  resources [OrderEvents]
}

deployment local for OrdersSystem {
  environment test
  target process
  services all
  bind OrderEvents memory
}
"""


class CoreConsumerExecutionContractTest(unittest.TestCase):
    def _analysis(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "consumer.aidl"
            source.write_text(text, encoding="utf-8")
            return load_compiler_analysis([source])

    def _materialization_diagnostics(self, text: str):
        return tuple(
            diagnostic
            for diagnostic in self._analysis(text).diagnostics
            if diagnostic.code.value == "AIDL-T005"
            and diagnostic.subject.kind == "consumer"
        )

    def _ir(self, text: str):
        analysis = self._analysis(text)
        errors = [
            item.to_json()
            for item in analysis.diagnostics
            if item.severity == CompilerDiagnosticSeverity.ERROR
        ]
        self.assertEqual([], errors)
        return build_canonical_ir(analysis)

    def _consumer_ir(self, text: str):
        ir = self._ir(text)
        return next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "consumer" and item.get("name") == "ApplyOrder"
        )

    def _source_with_start(self, kind: str, input_expression: str = "{ requestId: event.eventId }") -> str:
        source = _VALID_SOURCE.replace(
            "  retry: none\n}",
            f"  retry: none\n  start: {kind} ReviewOrder({input_expression})\n}}",
            1,
        ).replace(
            "runs [consumer ApplyOrder]",
            f"runs [consumer ApplyOrder, {kind} ReviewOrder]",
            1,
        )
        return source + f"""

value ReviewInput {{
  requestId: uuid required
}}

{kind} ReviewOrder(input: ReviewInput) -> uuid {{
}}
"""

    def test_service_binding_is_preserved_deterministically(self) -> None:
        first_analysis = self._analysis(_VALID_SOURCE)
        second_analysis = self._analysis(_VALID_SOURCE)
        first_errors = [
            item.to_json()
            for item in first_analysis.diagnostics
            if item.severity == CompilerDiagnosticSeverity.ERROR
        ]
        second_errors = [
            item.to_json()
            for item in second_analysis.diagnostics
            if item.severity == CompilerDiagnosticSeverity.ERROR
        ]
        self.assertEqual([], first_errors)
        self.assertEqual([], second_errors)

        first = build_canonical_ir(first_analysis)
        second = build_canonical_ir(second_analysis)
        first_consumer = next(
            item
            for item in first["declarations"]
            if item.get("kind") == "consumer" and item.get("name") == "ApplyOrder"
        )
        second_consumer = next(
            item
            for item in second["declarations"]
            if item.get("kind") == "consumer" and item.get("name") == "ApplyOrder"
        )
        service = next(
            item
            for item in first["system"]["services"]
            if item.get("name") == "OrdersService"
        )
        second_service = next(
            item
            for item in second["system"]["services"]
            if item.get("name") == "OrdersService"
        )

        self.assertEqual(first_consumer, second_consumer)
        self.assertEqual(service, second_service)
        self.assertEqual({"kind": "none"}, first_consumer["retry"])
        self.assertIsNone(first_consumer["effect"])
        self.assertIn(first_consumer["declarationId"], service["runs"])

    def test_unresolved_consumer_service_is_rejected_before_ir(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace("service OrdersService", "service MissingService", 1)
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("must resolve uniquely", diagnostics[0].message)

    def test_consumer_service_must_match_service_runs_contract(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace("runs [consumer ApplyOrder]", "runs []", 1)
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("does not list consumer", diagnostics[0].message)

    def test_exponential_retry_is_preserved_deterministically_in_ir(self) -> None:
        source = _VALID_SOURCE.replace(
            "retry: none",
            "retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)",
            1,
        )
        first = self._consumer_ir(source)
        second = self._consumer_ir(source)
        self.assertEqual(first, second)
        self.assertEqual(
            {
                "kind": "exponential",
                "attempts": 8,
                "initialDelayMs": 1000,
                "maxDelayMs": 300000,
            },
            first["retry"],
        )

    def test_malformed_exponential_retry_is_rejected_before_ir(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "retry: none",
                "retry: exponential(initial: 0s, maxDelay: 5m, attempts: 8)",
                1,
            )
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("retry policy 'exponential'", diagnostics[0].message)

    def test_immediate_retry_is_rejected_until_ir_projection_exists(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace("retry: none", "retry: immediate(max: 2)", 1)
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("retry policy 'immediate'", diagnostics[0].message)

    def test_workflow_and_task_start_are_preserved_deterministically_in_ir(self) -> None:
        for kind in ("workflow", "task"):
            with self.subTest(kind=kind):
                source = self._source_with_start(kind)
                first = self._ir(source)
                second = self._ir(source)
                first_consumer = next(
                    item
                    for item in first["declarations"]
                    if item.get("kind") == "consumer" and item.get("name") == "ApplyOrder"
                )
                second_consumer = next(
                    item
                    for item in second["declarations"]
                    if item.get("kind") == "consumer" and item.get("name") == "ApplyOrder"
                )
                first_target = next(
                    item
                    for item in first["declarations"]
                    if item.get("kind") == kind and item.get("name") == "ReviewOrder"
                )
                second_target = next(
                    item
                    for item in second["declarations"]
                    if item.get("kind") == kind and item.get("name") == "ReviewOrder"
                )
                self.assertEqual(first_consumer, second_consumer)
                self.assertEqual(first_target, second_target)
                self.assertEqual(
                    {
                        "kind": "start",
                        "targetKind": kind,
                        "targetId": first_target["declarationId"],
                        "input": {
                            "kind": "record",
                            "fields": [
                                {
                                    "name": "requestId",
                                    "value": {
                                        "kind": "symbol",
                                        "path": ["event", "eventId"],
                                    },
                                }
                            ],
                        },
                    },
                    first_consumer["effect"],
                )

    def test_unresolved_consumer_start_target_is_rejected_before_ir(self) -> None:
        source = _VALID_SOURCE.replace(
            "  retry: none\n}",
            "  retry: none\n  start: workflow MissingOrder({ requestId: event.eventId })\n}",
            1,
        )
        diagnostics = self._materialization_diagnostics(source)
        self.assertEqual(1, len(diagnostics))
        self.assertIn("start target 'workflow MissingOrder' must resolve uniquely", diagnostics[0].message)

    def test_unprojectable_consumer_start_input_is_rejected_before_ir(self) -> None:
        source = self._source_with_start("workflow", "event.eventId + 1")
        diagnostics = self._materialization_diagnostics(source)
        self.assertEqual(1, len(diagnostics))
        self.assertIn("start input", diagnostics[0].message)
        self.assertIn("not losslessly projectable", diagnostics[0].message)

    def test_start_saga_is_rejected_at_normative_grammar_boundary(self) -> None:
        source = _VALID_SOURCE.replace(
            "  retry: none\n}",
            "  retry: none\n  start: saga ReviewOrder({ requestId: event.eventId })\n}",
            1,
        ) + """

value ReviewInput {
  requestId: uuid required
}

saga ReviewOrder(input: ReviewInput) -> uuid {
}
"""
        diagnostics = self._materialization_diagnostics(source)
        self.assertEqual(1, len(diagnostics))
        self.assertIn("start kind 'saga'", diagnostics[0].message)
        self.assertIn("normative consumer invocationKind grammar", diagnostics[0].message)

    def test_start_mutation_is_rejected_without_inventing_semantics(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "  retry: none\n}",
                "  retry: none\n  start: mutation ApplyOrder(event.eventId)\n}",
                1,
            )
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("start kind 'mutation'", diagnostics[0].message)
        self.assertIn("no closed Core Canonical IR start target kind", diagnostics[0].message)

    def test_call_and_consumer_transaction_are_rejected_at_full_ir_boundary(self) -> None:
        call_diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "  retry: none\n}",
                "  retry: none\n  call: task ReviewOrder(event.eventId)\n}",
                1,
            )
        )
        self.assertEqual(1, len(call_diagnostics))
        self.assertIn("consumer call", call_diagnostics[0].message)

        transaction_diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "  retry: none\n}",
                "  retry: none\n  transaction on OrdersDb {\n  }\n}",
                1,
            )
        )
        self.assertEqual(1, len(transaction_diagnostics))
        self.assertIn("consumer transaction", transaction_diagnostics[0].message)

    def test_isolated_m2_consumer_rules_remain_independent(self) -> None:
        text = """module example.orders
consumer ApplyOrder {
  call: refreshOrder(event.id)
}
"""
        diagnostics = self._analysis(text).diagnostics
        self.assertEqual(["AIDL-DIST411"], [item.code.value for item in diagnostics])


if __name__ == "__main__":
    unittest.main()
