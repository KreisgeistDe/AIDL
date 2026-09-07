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
  retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)
  start: workflow ReviewOrder(event.eventId)
}

workflow ReviewOrder(eventId: uuid) -> uuid {
}

service OrdersService {
  uses [OrderEvents]
  runs [consumer ApplyOrder, workflow ReviewOrder]
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

    def test_service_retry_and_start_are_preserved_deterministically(self) -> None:
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
        workflow = next(
            item
            for item in first["declarations"]
            if item.get("kind") == "workflow" and item.get("name") == "ReviewOrder"
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
        self.assertEqual(
            {
                "kind": "exponential",
                "attempts": 8,
                "initialDelayMs": 1000,
                "maxDelayMs": 300000,
            },
            first_consumer["retry"],
        )
        self.assertEqual("start", first_consumer["effect"]["kind"])
        self.assertEqual("workflow", first_consumer["effect"]["targetKind"])
        self.assertEqual(workflow["declarationId"], first_consumer["effect"]["targetId"])
        self.assertIn(first_consumer["declarationId"], service["runs"])

    def test_unresolved_consumer_service_is_rejected_before_ir(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace("service OrdersService", "service MissingService", 1)
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("must resolve uniquely", diagnostics[0].message)

    def test_consumer_service_must_match_service_runs_contract(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "runs [consumer ApplyOrder, workflow ReviewOrder]",
                "runs [workflow ReviewOrder]",
                1,
            )
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("does not list consumer", diagnostics[0].message)

    def test_exponential_retry_requires_fully_materializable_budget(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "exponential(initial: 1s, maxDelay: 5m, attempts: 8)",
                "exponential(initial: 1s, maxDelay: 5m)",
                1,
            )
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("initial, maxDelay, and attempts", diagnostics[0].message)

    def test_immediate_retry_is_rejected_only_at_full_ir_materialization_boundary(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "exponential(initial: 1s, maxDelay: 5m, attempts: 8)",
                "immediate(max: 2)",
                1,
            )
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("retry policy 'immediate'", diagnostics[0].message)

    def test_start_target_must_resolve_before_ir(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace("ReviewOrder(event.eventId)", "MissingWorkflow(event.eventId)", 1)
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("must resolve uniquely", diagnostics[0].message)

    def test_start_mutation_is_rejected_without_inventing_ir_semantics(self) -> None:
        diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "start: workflow ReviewOrder(event.eventId)",
                "start: mutation ApplyOrder(event.eventId)",
                1,
            )
        )
        self.assertEqual(1, len(diagnostics))
        self.assertIn("start mutation", diagnostics[0].message)

    def test_call_and_consumer_transaction_are_rejected_at_full_ir_boundary(self) -> None:
        call_diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "start: workflow ReviewOrder(event.eventId)",
                "call: task ReviewOrder(event.eventId)",
                1,
            )
        )
        self.assertEqual(1, len(call_diagnostics))
        self.assertIn("consumer call", call_diagnostics[0].message)

        transaction_diagnostics = self._materialization_diagnostics(
            _VALID_SOURCE.replace(
                "start: workflow ReviewOrder(event.eventId)",
                "transaction on OrdersDb {\n  }",
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
