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


class CoreConsumerIdempotencySemanticsTest(unittest.TestCase):
    def test_ir_preserves_consumer_idempotency_key_scope_and_retention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_VALID_SOURCE, encoding="utf-8")
            analysis = load_compiler_analysis([source])
            errors = [
                item.to_json()
                for item in analysis.diagnostics
                if item.severity == CompilerDiagnosticSeverity.ERROR
            ]
            self.assertEqual([], errors)
            ir = build_canonical_ir(analysis)

        consumer = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "consumer" and item.get("name") == "ApplyOrder"
        )
        event = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "event" and item.get("name") == "OrderApplied"
        )
        topic = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "topic" and item.get("name") == "OrderEvents"
        )

        self.assertEqual(event["declarationId"], consumer["eventId"])
        self.assertEqual(topic["declarationId"], consumer["topicId"])
        self.assertEqual(
            {
                "key": {"kind": "symbol", "path": ["event . eventId"]},
                "scope": {"kind": "literal", "value": "consumer"},
                "retentionMs": 604800000,
            },
            consumer["idempotency"],
        )

    def test_effectful_consumer_without_idempotency_is_rejected_before_ir(self) -> None:
        source_text = """module example.orders
consumer ApplyOrder {
  call: refreshOrder(event.id)
}
"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "consumer.aidl"
            source.write_text(source_text, encoding="utf-8")
            analysis = load_compiler_analysis([source])

        diagnostics = [item for item in analysis.diagnostics if item.code == "AIDL-DIST411"]
        self.assertEqual(1, len(diagnostics))
        self.assertEqual(
            "effectful consumer 'example.orders.ApplyOrder' must declare exactly one 'idempotency' clause; found 0",
            diagnostics[0].message,
        )
        self.assertEqual((2, 1), (diagnostics[0].location.line, diagnostics[0].location.column))


if __name__ == "__main__":
    unittest.main()
