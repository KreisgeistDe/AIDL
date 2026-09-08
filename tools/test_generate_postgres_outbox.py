from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.generate_postgres_outbox import (
    GENERATED_MIGRATION_PATH,
    GENERATED_OUTBOX_PATH,
    PostgresOutboxGeneratorError,
    generate_postgres_outbox_files,
)
from tools.generate_postgres_transactions import generate_postgres_transactions


def _identity(kind: str, name: str, module: str) -> dict[str, object]:
    fqn = f"{module}.{name}"
    return {
        "kind": kind,
        "declarationId": f"{fqn}@1",
        "fqn": fqn,
        "name": name,
        "ownerModule": module,
        "semanticHash": "sha256:" + "0" * 64,
    }


def _event() -> dict[str, object]:
    return {
        **_identity("event", "PetUpdated", "petstore.contracts"),
        "majorVersion": 1,
        "fields": [
            {"name": "eventId", "type": {"kind": "scalar", "name": "string"}, "required": True, "mutable": False, "sensitive": False, "generated": False},
            {"name": "petId", "type": {"kind": "scalar", "name": "uuid"}, "required": True, "mutable": False, "sensitive": False, "generated": False},
            {"name": "occurredAt", "type": {"kind": "scalar", "name": "datetime"}, "required": True, "mutable": False, "sensitive": False, "generated": False},
        ],
    }


def _topic() -> dict[str, object]:
    return {
        **_identity("topic", "PetEvents", "petstore.contracts"),
        "eventIds": ["petstore.contracts.PetUpdated@1"],
        "delivery": "atLeastOnce",
        "partitionField": "petId",
        "ordering": "perPartition",
        "retentionMs": 2_592_000_000,
        "compatibility": "backward",
        "deadLetterAttempts": 8,
    }


def _mutation() -> dict[str, object]:
    return {
        **_identity("mutation", "updatePet", "petstore.operations"),
        "input": {"kind": "record", "fields": []},
        "output": {"kind": "record", "fields": []},
        "auth": {"mode": "authenticated"},
        "allow": {"kind": "literal", "value": True},
        "errorIds": [],
        "idempotency": {
            "key": {"kind": "symbol", "path": ["input", "operationId"]},
            "scope": {"kind": "literal", "value": "mutation"},
            "retentionMs": 86_400_000,
        },
        "rootEffect": {
            "kind": "transaction",
            "resourceId": "petstore.system.PetstoreDb@1",
            "isolation": "readCommitted",
            "steps": [
                {
                    "kind": "publish",
                    "eventId": "petstore.contracts.PetUpdated@1",
                    "topicId": "petstore.contracts.PetEvents@1",
                    "payload": {
                        "kind": "record",
                        "fields": [
                            {"name": "eventId", "value": {"kind": "symbol", "path": ["input", "eventId"]}},
                            {"name": "petId", "value": {"kind": "symbol", "path": ["input", "petId"]}},
                            {"name": "occurredAt", "value": {"kind": "symbol", "path": ["input", "occurredAt"]}},
                        ],
                    },
                    "via": "outbox",
                }
            ],
            "result": {"kind": "literal", "value": None},
        },
    }


def _ir(declarations: list[dict[str, object]] | None = None) -> dict[str, object]:
    declarations = declarations or [_event(), _topic(), _mutation()]
    return {
        "irVersion": "0.3.0",
        "declarations": declarations,
        "system": {
            "resources": [
                {
                    "declarationId": "petstore.system.PetstoreDb@1",
                    "fqn": "petstore.system.PetstoreDb",
                    "resourceKind": "sql",
                    "transactionIsolation": ["readCommitted", "serializable"],
                }
            ],
            "services": [],
        },
    }


_SOURCE_TO_RUNTIME = """module recovery

app RecoveryApp {
  profile core version 1
  profile distributed version 1
  system RecoverySystem
  defaultDeployment local
}

auth {
  provider oidc
  subject claim "sub"
  roles [user]
  scopes [things.write]
  serviceIdentities required
}

export value CreateThingInput {
  operationId: uuid required
  id: uuid required
  name: string(1..80) required
}

export entity Thing {
  id: uuid primary immutable
  name: string(1..80) required immutable
}

export event ThingCreated version 1 {
  eventId: uuid required
  thingId: uuid required
  occurredAt: datetime required
}

export topic ThingEvents {
  events [ThingCreated]
  delivery atLeastOnce
  partition by thingId
  ordering perPartition
  retention 30d
  compatibility backward
  deadLetter after 8 attempts
}

export mutation createThing(input: CreateThingInput) -> Thing {
  auth: authenticated
  allow: true
  errors: []
  idempotency: input.operationId retain 1d
  transaction on Db isolation readCommitted {
    thing = Thing.create(id: input.id, name: input.name)
    emit: ThingCreated(eventId: operationId(), thingId: thing.id, occurredAt: now()) to ThingEvents via outbox
    return thing
  }
}

export resource Db sql {
  consistency strong
  transactions [readCommitted]
  migrations expandBackfillContract
  encryption required
}

export service RecoveryService {
  owns [Thing]
  uses [Db, ThingEvents]
  exposes [mutation createThing]
  runs []
  reliability {
    idempotencyStore Db
  }
}

export system RecoverySystem {
  services [RecoveryService]
  resources [Db, ThingEvents]
  apis []
}

export deployment local for RecoverySystem {
  environment test
  target process
  colocate services all
  bind Db memory
  bind ThingEvents memory
}
"""


class PostgresOutboxGeneratorTest(unittest.TestCase):
    def test_generates_deterministic_outbox_runtime_migration_and_atomic_transaction_insert(self) -> None:
        event, topic, mutation = _event(), _topic(), _mutation()
        files = generate_postgres_outbox_files(_ir([event, topic, mutation]))
        reversed_files = generate_postgres_outbox_files(_ir([mutation, topic, event]))

        self.assertEqual(files, reversed_files)
        self.assertEqual(set(files), {GENERATED_OUTBOX_PATH, GENERATED_MIGRATION_PATH})
        runtime = files[GENERATED_OUTBOX_PATH]
        migration = files[GENERATED_MIGRATION_PATH]
        self.assertIn('"eventFqn":"petstore.contracts.PetUpdated"', runtime)
        self.assertIn('"topicFqn":"petstore.contracts.PetEvents"', runtime)
        self.assertIn('FOR UPDATE SKIP LOCKED LIMIT $1', runtime)
        self.assertIn('markOutboxPublished', runtime)
        self.assertIn('CREATE TABLE IF NOT EXISTS "aidl_outbox"', migration)
        self.assertIn('"event_id" text NOT NULL UNIQUE', migration)
        self.assertIn('WHERE "published_at" IS NULL', migration)

        transaction_runtime = generate_postgres_transactions(_ir([event, topic, mutation]))
        self.assertIn('"kind":"publish"', transaction_runtime)
        self.assertIn('INSERT INTO \\"aidl_outbox\\"', transaction_runtime)
        self.assertIn('await client.query("BEGIN")', transaction_runtime)
        self.assertIn('await client.query("COMMIT")', transaction_runtime)
        self.assertIn('if (kind === "publish")', transaction_runtime)

    def test_serializes_retry_sql_literal_without_changing_sql_semantics(self) -> None:
        runtime = generate_postgres_outbox_files(_ir())[GENERATED_OUTBOX_PATH]
        sql = 'UPDATE "aidl_outbox" SET "available_at" = CURRENT_TIMESTAMP + ($2 * INTERVAL \'1 millisecond\') WHERE "sequence" = $1 AND "published_at" IS NULL'
        self.assertIn(json.dumps(sql, ensure_ascii=False), runtime)
        self.assertIn("INTERVAL '1 millisecond'", runtime)

    def test_source_to_ir_to_runtime_executes_current_intrinsics_and_create_binding_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.aidl"
            path.write_text(_SOURCE_TO_RUNTIME, encoding="utf-8")
            ir = build_canonical_ir(load_compiler_analysis([path]))

        mutation = next(item for item in ir["declarations"] if item.get("name") == "createThing")
        steps = mutation["rootEffect"]["steps"]
        create = next(step for step in steps if step.get("kind") == "write" and step.get("action") == "create")
        publish = next(step for step in steps if step.get("kind") == "publish")
        payload = {field["name"]: field["value"] for field in publish["payload"]["fields"]}

        self.assertNotIn("bind", create)
        self.assertEqual({"kind": "call", "function": "operationId", "arguments": []}, payload["eventId"])
        self.assertEqual({"kind": "symbol", "path": ["thing", "id"]}, payload["thingId"])
        self.assertEqual({"kind": "call", "function": "now", "arguments": []}, payload["occurredAt"])

        runtime = generate_postgres_transactions(ir)
        self.assertIn('"bind":"thing","kind":"create"', runtime)
        self.assertIn('if (fn === "operationId")', runtime)
        self.assertIn('if (fn === "now")', runtime)
        self.assertIn('const transactionNow = new Date().toISOString()', runtime)
        self.assertIn('bindings[String(step.bind)] = row', runtime)
        self.assertIn('INSERT INTO \\"aidl_outbox\\"', runtime)

    def test_rejects_topic_that_does_not_declare_event_or_at_least_once_delivery(self) -> None:
        topic = _topic()
        topic["eventIds"] = []
        with self.assertRaisesRegex(PostgresOutboxGeneratorError, "does not declare event"):
            generate_postgres_outbox_files(_ir([_event(), topic, _mutation()]))

        topic = _topic()
        topic["delivery"] = "atMostOnce"
        with self.assertRaisesRegex(PostgresOutboxGeneratorError, "at-least-once outbox subset"):
            generate_postgres_outbox_files(_ir([_event(), topic, _mutation()]))

    def test_rejects_missing_required_or_partition_payload_fields(self) -> None:
        mutation = _mutation()
        payload = mutation["rootEffect"]["steps"][0]["payload"]  # type: ignore[index]
        payload["fields"] = [field for field in payload["fields"] if field["name"] != "occurredAt"]  # type: ignore[index]
        with self.assertRaisesRegex(PostgresOutboxGeneratorError, "misses required payload fields"):
            generate_postgres_outbox_files(_ir([_event(), _topic(), mutation]))

        mutation = _mutation()
        payload = mutation["rootEffect"]["steps"][0]["payload"]  # type: ignore[index]
        payload["fields"] = [field for field in payload["fields"] if field["name"] != "petId"]  # type: ignore[index]
        with self.assertRaisesRegex(PostgresOutboxGeneratorError, "misses required payload fields"):
            generate_postgres_outbox_files(_ir([_event(), _topic(), mutation]))

    def test_rejects_non_outbox_publish_unknown_producer_call_and_unsupported_ir_version(self) -> None:
        mutation = _mutation()
        mutation["rootEffect"]["steps"][0]["via"] = "direct"  # type: ignore[index]
        with self.assertRaisesRegex(PostgresOutboxGeneratorError, "via=outbox"):
            generate_postgres_outbox_files(_ir([_event(), _topic(), mutation]))

        mutation = _mutation()
        payload = mutation["rootEffect"]["steps"][0]["payload"]  # type: ignore[index]
        payload["fields"][0]["value"] = {"kind": "symbol", "path": ["randomId()"]}  # type: ignore[index]
        with self.assertRaisesRegex(PostgresOutboxGeneratorError, "executable subset"):
            generate_postgres_outbox_files(_ir([_event(), _topic(), mutation]))

        ir = _ir()
        ir["irVersion"] = "0.2.0"
        with self.assertRaisesRegex(PostgresOutboxGeneratorError, "unsupported canonical IR version"):
            generate_postgres_outbox_files(ir)


if __name__ == "__main__":
    unittest.main()
