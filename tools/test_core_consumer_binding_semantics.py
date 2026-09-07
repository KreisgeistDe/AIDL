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
  idempotency: event.eventId retain 7d
}

system OrdersSystem {
  services []
  resources [OrderEvents]
}

deployment local for OrdersSystem {
  environment test
  target process
  bind OrderEvents memory
}
"""


class CoreConsumerBindingSemanticsTest(unittest.TestCase):
    def _analysis(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "consumer.aidl"
            source.write_text(text, encoding="utf-8")
            return load_compiler_analysis([source])

    def _binding_diagnostics(self, text: str):
        return tuple(
            diagnostic
            for diagnostic in self._analysis(text).diagnostics
            if diagnostic.code.value == "AIDL-DIST415"
        )

    def test_valid_binding_is_diagnostic_free_and_preserved_in_ir(self) -> None:
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
        event = next(
            item
            for item in first["declarations"]
            if item.get("kind") == "event" and item.get("name") == "OrderApplied"
        )
        topic = next(
            item
            for item in first["declarations"]
            if item.get("kind") == "topic" and item.get("name") == "OrderEvents"
        )

        self.assertEqual(first_consumer, second_consumer)
        self.assertEqual(event["declarationId"], first_consumer["eventId"])
        self.assertEqual(topic["declarationId"], first_consumer["topicId"])
        self.assertEqual(
            {
                "key": {"kind": "symbol", "path": ["event . eventId"]},
                "scope": {"kind": "literal", "value": "consumer"},
                "retentionMs": 604800000,
            },
            first_consumer["idempotency"],
        )

    def test_invalid_core_bindings_have_stable_source_diagnostics(self) -> None:
        cases = {
            "missing header": (
                _VALID_SOURCE.replace(
                    "consumer ApplyOrder on OrderApplied from OrderEvents {",
                    "consumer ApplyOrder {",
                    1,
                ),
                "must declare 'on EVENT from TOPIC'",
            ),
            "unresolved event": (
                _VALID_SOURCE.replace(
                    "on OrderApplied from OrderEvents",
                    "on MissingEvent from OrderEvents",
                    1,
                ),
                "event 'MissingEvent' must resolve uniquely; found 0 matching event declarations",
            ),
            "unresolved topic": (
                _VALID_SOURCE.replace(
                    "on OrderApplied from OrderEvents",
                    "on OrderApplied from MissingTopic",
                    1,
                ),
                "topic 'MissingTopic' must resolve uniquely; found 0 matching topic declarations",
            ),
            "event not in topic": (
                _VALID_SOURCE.replace(
                    "events [OrderApplied]",
                    "events [OtherEvent]",
                    1,
                ).replace(
                    "event OrderApplied version 1 {",
                    "event OtherEvent version 1 {\n  eventId: uuid required\n}\n\nevent OrderApplied version 1 {",
                    1,
                ),
                "is not declared by topic 'example.orders.OrderEvents'",
            ),
            "at most once": (
                _VALID_SOURCE.replace("delivery atLeastOnce", "delivery atMostOnce", 1),
                "requires topic 'example.orders.OrderEvents' delivery atLeastOnce; found atMostOnce",
            ),
            "implicit delivery": (
                _VALID_SOURCE.replace("  delivery atLeastOnce\n", "", 1),
                "requires topic 'example.orders.OrderEvents' delivery atLeastOnce; found none",
            ),
        }

        for name, (source, message_fragment) in cases.items():
            with self.subTest(name=name):
                diagnostics = self._binding_diagnostics(source)
                self.assertEqual(1, len(diagnostics))
                diagnostic = diagnostics[0]
                self.assertIn(message_fragment, diagnostic.message)
                self.assertEqual("policy", diagnostic.phase)
                self.assertEqual("error", diagnostic.severity.value)
                self.assertEqual(
                    {"kind": "consumer", "name": "ApplyOrder"},
                    diagnostic.subject.to_json(),
                )
                self.assertEqual(
                    "aidl://diagnostics/AIDL-DIST415",
                    diagnostic.docs,
                )


if __name__ == "__main__":
    unittest.main()
