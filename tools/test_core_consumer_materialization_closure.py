from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))


_BASE_SOURCE = """module example.orders

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
  idempotency:
  {
    key event.eventId
    scope "orders"
    retain 7d
  }
  retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)
  start: workflow ReviewOrder({ requestId: event.eventId })
}

value ReviewInput {
  requestId: uuid required
}

workflow ReviewOrder(input: ReviewInput) -> uuid {
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


class CoreConsumerMaterializationClosureTest(unittest.TestCase):
    def _analysis(self, text: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "consumer.aidl"
        source.write_text(text, encoding="utf-8")
        return load_compiler_analysis([source])

    def _errors(self, text: str):
        return tuple(
            diagnostic
            for diagnostic in self._analysis(text).diagnostics
            if diagnostic.severity == CompilerDiagnosticSeverity.ERROR
        )

    def _ir(self, text: str) -> dict:
        analysis = self._analysis(text)
        self.assertEqual([], [item.to_json() for item in analysis.diagnostics if item.severity == CompilerDiagnosticSeverity.ERROR])
        return build_canonical_ir(analysis)

    @staticmethod
    def _consumer(document: dict) -> dict:
        return next(
            item
            for item in document["declarations"]
            if item.get("kind") == "consumer" and item.get("name") == "ApplyOrder"
        )

    def _assert_schema_valid(self, document: dict) -> None:
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        self.assertEqual((), tuple(validator.iter_errors(document)))

    def test_complete_consumer_contract_is_deterministic_and_schema_valid(self) -> None:
        first = self._ir(_BASE_SOURCE)
        second = self._ir(_BASE_SOURCE)
        self.assertEqual(first, second)
        self._assert_schema_valid(first)

        consumer = self._consumer(first)
        event = next(item for item in first["declarations"] if item.get("kind") == "event")
        topic = next(item for item in first["declarations"] if item.get("kind") == "topic")
        service = next(item for item in first["system"]["services"] if item.get("name") == "OrdersService")
        workflow = next(item for item in first["declarations"] if item.get("kind") == "workflow")

        self.assertEqual("example.orders.ApplyOrder", consumer["fqn"])
        self.assertEqual("example.orders.ApplyOrder@1", consumer["declarationId"])
        self.assertEqual(event["declarationId"], consumer["eventId"])
        self.assertEqual(topic["declarationId"], consumer["topicId"])
        self.assertIn(consumer["declarationId"], service["runs"])
        self.assertEqual(
            {
                "key": {"kind": "symbol", "path": ["event", "eventId"]},
                "scope": {"kind": "literal", "value": "orders"},
                "retentionMs": 604800000,
            },
            consumer["idempotency"],
        )
        self.assertEqual(
            {
                "kind": "exponential",
                "attempts": 8,
                "initialDelayMs": 1000,
                "maxDelayMs": 300000,
            },
            consumer["retry"],
        )
        self.assertEqual(
            {
                "kind": "start",
                "targetKind": "workflow",
                "targetId": workflow["declarationId"],
                "input": {
                    "kind": "record",
                    "fields": [
                        {
                            "name": "requestId",
                            "value": {"kind": "symbol", "path": ["event", "eventId"]},
                        }
                    ],
                },
            },
            consumer["effect"],
        )
        source_entry = next(
            entry
            for entry in first["sourceMap"]["entries"]
            if entry["originalDeclarationId"] == consumer["declarationId"]
        )
        consumer_index = next(
            index
            for index, item in enumerate(first["declarations"])
            if item.get("declarationId") == consumer["declarationId"]
        )
        self.assertEqual(f"/declarations/{consumer_index}", source_entry["nodePath"])

    def test_task_start_is_losslessly_projected(self) -> None:
        source = _BASE_SOURCE.replace("workflow ReviewOrder", "task ReviewOrder").replace(
            "start: workflow ReviewOrder", "start: task ReviewOrder"
        ).replace("workflow ReviewOrder]", "task ReviewOrder]")
        document = self._ir(source)
        consumer = self._consumer(document)
        task = next(item for item in document["declarations"] if item.get("kind") == "task")
        self.assertEqual("task", consumer["effect"]["targetKind"])
        self.assertEqual(task["declarationId"], consumer["effect"]["targetId"])
        self._assert_schema_valid(document)

    def test_optional_consumer_facts_have_explicit_closed_defaults(self) -> None:
        source = _BASE_SOURCE
        source = source.replace(
            "  idempotency:\n  {\n    key event.eventId\n    scope \"orders\"\n    retain 7d\n  }\n",
            "",
        )
        source = source.replace("  retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)\n", "")
        source = source.replace("  start: workflow ReviewOrder({ requestId: event.eventId })\n", "")
        source = source.replace(", workflow ReviewOrder", "")
        document = self._ir(source)
        consumer = self._consumer(document)
        self.assertEqual({"kind": "none"}, consumer["retry"])
        self.assertIsNone(consumer["effect"])
        self.assertNotIn("idempotency", consumer)
        self._assert_schema_valid(document)

    def test_binding_failures_keep_dist415_ownership_without_t005_duplicate(self) -> None:
        cases = (
            _BASE_SOURCE.replace("on OrderApplied from OrderEvents", "on MissingEvent from OrderEvents"),
            _BASE_SOURCE.replace("on OrderApplied from OrderEvents", "on OrderApplied from MissingTopic"),
            _BASE_SOURCE.replace("events [OrderApplied]", "events []"),
            _BASE_SOURCE.replace("delivery atLeastOnce", "delivery atMostOnce"),
        )
        for source in cases:
            with self.subTest(source=source.split("consumer", 1)[1][:80]):
                errors = self._errors(source)
                codes = [item.code.value for item in errors if item.subject.kind == "consumer"]
                self.assertIn("AIDL-DIST415", codes)
                self.assertNotIn("AIDL-T005", codes)

    def test_idempotency_failures_keep_dist411_ownership_without_t005_duplicate(self) -> None:
        missing = _BASE_SOURCE.replace(
            "  idempotency:\n  {\n    key event.eventId\n    scope \"orders\"\n    retain 7d\n  }\n",
            "",
        )
        duplicate = _BASE_SOURCE.replace(
            "  retry: exponential",
            "  idempotency: event.eventId retain 7d\n  retry: exponential",
            1,
        )
        for source in (missing, duplicate):
            with self.subTest(duplicate=source is duplicate):
                errors = self._errors(source)
                codes = [item.code.value for item in errors if item.subject.kind == "consumer"]
                self.assertIn("AIDL-DIST411", codes)
                self.assertNotIn("AIDL-T005", codes)

    def test_materialization_only_consumer_losses_are_rejected_with_t005(self) -> None:
        cases = {
            "service-unresolved": _BASE_SOURCE.replace("service OrdersService", "service MissingService", 1),
            "service-runs-mismatch": _BASE_SOURCE.replace("runs [consumer ApplyOrder, workflow ReviewOrder]", "runs [workflow ReviewOrder]"),
            "retry-immediate": _BASE_SOURCE.replace("retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)", "retry: immediate(max: 2)"),
            "retry-malformed": _BASE_SOURCE.replace("retry: exponential(initial: 1s, maxDelay: 5m, attempts: 8)", "retry: exponential(initial: 0s, maxDelay: 5m, attempts: 8)"),
            "start-mutation": _BASE_SOURCE.replace("start: workflow ReviewOrder", "start: mutation ReviewOrder"),
            "start-saga": _BASE_SOURCE.replace("start: workflow ReviewOrder", "start: saga ReviewOrder"),
            "start-unresolved": _BASE_SOURCE.replace("start: workflow ReviewOrder", "start: workflow MissingOrder"),
            "start-unprojectable": _BASE_SOURCE.replace("{ requestId: event.eventId }", "event.eventId + 1", 1),
            "call": _BASE_SOURCE.replace("  start: workflow ReviewOrder({ requestId: event.eventId })\n", "  call: task ReviewOrder(event.eventId)\n"),
            "transaction": _BASE_SOURCE.replace(
                "  start: workflow ReviewOrder({ requestId: event.eventId })\n",
                "  transaction on OrdersDb {\n  }\n",
            ),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                errors = self._errors(source)
                t005 = [
                    item
                    for item in errors
                    if item.code.value == "AIDL-T005" and item.subject.kind == "consumer"
                ]
                self.assertEqual(1, len(t005), [item.to_json() for item in errors])


if __name__ == "__main__":
    unittest.main()
