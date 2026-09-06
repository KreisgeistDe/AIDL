from __future__ import annotations

import unittest

from tools.generate_postgres_transactions import (
    GENERATED_TRANSACTIONS_PATH,
    PostgresTransactionGeneratorError,
    generate_postgres_transaction_files,
    generate_postgres_transactions,
)


def _identity(kind: str, name: str, module: str = "petstore") -> dict[str, object]:
    fqn = f"{module}.{name}"
    return {
        "kind": kind,
        "declarationId": f"{fqn}@1",
        "fqn": fqn,
        "name": name,
        "ownerModule": module,
        "semanticHash": "sha256:" + "0" * 64,
    }


def _field(name: str, type_ref: dict[str, object], **extra: object) -> dict[str, object]:
    return {
        "name": name,
        "type": type_ref,
        "required": True,
        "mutable": False,
        "sensitive": False,
        "generated": False,
        **extra,
    }


def _base_ir(*, isolation: str = "serializable", expected: bool = True, include_publish: bool = False) -> dict[str, object]:
    entity = {
        **_identity("entity", "Pet", "petstore.domain"),
        "fields": [
            _field("id", {"kind": "scalar", "name": "uuid"}, primary=True, generated=True),
            _field("revision", {"kind": "scalar", "name": "revision"}, concurrencyToken=True, generated=True),
            _field("name", {"kind": "scalar", "name": "string"}, mutable=True),
        ],
        "identityFields": ["id"],
    }
    read = {
        "kind": "read",
        "bind": "pet",
        "read": {
            "entityId": "petstore.domain.Pet@1",
            "steps": [{"kind": "require", "arguments": [{"kind": "symbol", "path": ["input", "petId"]}]}],
        },
        "elseErrorId": "aidl.std.NotFound@1",
    }
    update: dict[str, object] = {
        "kind": "write",
        "action": "update",
        "entityId": "petstore.domain.Pet@1",
        "target": {"kind": "symbol", "path": ["pet"]},
        "values": [{"field": "name", "value": {"kind": "symbol", "path": ["input", "name"]}}],
        "elseErrorId": "aidl.std.ConcurrentChange@1",
    }
    if expected:
        update["expectedRevision"] = {"kind": "symbol", "path": ["input", "expectedRevision"]}
    steps: list[dict[str, object]] = [read, update]
    declarations: list[dict[str, object]] = []
    if include_publish:
        event = {
            **_identity("event", "PetUpdated", "petstore.contracts"),
            "majorVersion": 1,
            "fields": [
                _field("eventId", {"kind": "scalar", "name": "string"}),
                _field("petId", {"kind": "scalar", "name": "uuid"}),
                _field("occurredAt", {"kind": "scalar", "name": "datetime"}),
            ],
        }
        topic = {
            **_identity("topic", "PetEvents", "petstore.contracts"),
            "eventIds": ["petstore.contracts.PetUpdated@1"],
            "delivery": "atLeastOnce",
            "partitionField": "petId",
            "ordering": "perPartition",
            "retentionMs": 86_400_000,
            "compatibility": "backward",
            "deadLetterAttempts": 8,
        }
        steps.append(
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
        )
        declarations.extend([event, topic])
    mutation = {
        **_identity("mutation", "UpdatePet", "petstore.operations"),
        "rootEffect": {
            "kind": "transaction",
            "resourceId": "petstore.system.PetstoreDb@1",
            "isolation": isolation,
            "steps": steps,
            "result": {"kind": "symbol", "path": ["pet"]},
        },
    }
    declarations.extend([mutation, entity])
    return {
        "irVersion": "0.3.0",
        "declarations": declarations,
        "system": {
            "resources": [
                {
                    "declarationId": "petstore.system.PetstoreDb@1",
                    "resourceKind": "sql",
                    "transactionIsolation": ["readCommitted", "repeatableRead", "serializable"],
                }
            ]
        },
    }


def _create_ir(*, assign_revision: bool = False) -> dict[str, object]:
    entity = {
        **_identity("entity", "Pet", "petstore.domain"),
        "fields": [
            _field("id", {"kind": "scalar", "name": "uuid"}, primary=True),
            _field("revision", {"kind": "scalar", "name": "revision"}, concurrencyToken=True, generated=True),
            _field("name", {"kind": "scalar", "name": "string"}, mutable=True),
        ],
        "identityFields": ["id"],
    }
    values: list[dict[str, object]] = [
        {"field": "id", "value": {"kind": "symbol", "path": ["input", "id"]}},
        {"field": "name", "value": {"kind": "symbol", "path": ["input", "name"]}},
    ]
    if assign_revision:
        values.append({"field": "revision", "value": {"kind": "symbol", "path": ["input", "revision"]}})
    mutation = {
        **_identity("mutation", "CreatePet", "petstore.operations"),
        "rootEffect": {
            "kind": "transaction",
            "resourceId": "petstore.system.PetstoreDb@1",
            "isolation": "readCommitted",
            "steps": [
                {
                    "kind": "write",
                    "action": "create",
                    "entityId": "petstore.domain.Pet@1",
                    "values": values,
                }
            ],
            "result": {"kind": "symbol", "path": ["pet"]},
        },
    }
    return {
        "irVersion": "0.3.0",
        "declarations": [mutation, entity],
        "system": {
            "resources": [
                {
                    "declarationId": "petstore.system.PetstoreDb@1",
                    "resourceKind": "sql",
                    "transactionIsolation": ["readCommitted"],
                }
            ]
        },
    }


class PostgresTransactionGeneratorTest(unittest.TestCase):
    def test_generates_transaction_boundary_and_atomic_revision_compare_and_set(self) -> None:
        ir = _base_ir()
        generated = generate_postgres_transactions(ir)
        files = generate_postgres_transaction_files(ir)

        self.assertEqual(files, {GENERATED_TRANSACTIONS_PATH: generated})
        self.assertIn('await client.query("BEGIN")', generated)
        self.assertIn('SET TRANSACTION ISOLATION LEVEL ${plan.isolationSql}', generated)
        self.assertIn('await client.query("COMMIT")', generated)
        self.assertIn('await client.query("ROLLBACK")', generated)
        self.assertIn('"isolationSql":"SERIALIZABLE"', generated)
        self.assertIn('SELECT * FROM \\"petstore_domain_pet\\" WHERE \\"id\\" = $1', generated)
        self.assertIn('UPDATE \\"petstore_domain_pet\\" SET \\"name\\" = $1, \\"revision\\" = \\"revision\\" + 1 WHERE \\"id\\" = $2 AND \\"revision\\" = $3 RETURNING *', generated)
        self.assertIn('"expectedRevision":{"kind":"symbol","path":["input","expectedRevision"]}', generated)
        self.assertIn('throw new AidlTransactionError(String(step.elseErrorId))', generated)
        self.assertIn('executeUpdatePetTransaction', generated)
        self.assertNotIn("idempotency", generated.lower())
        self.assertNotIn('"kind":"publish"', generated)

    def test_create_omits_store_owned_revision_and_returns_created_binding(self) -> None:
        generated = generate_postgres_transactions(_create_ir())

        self.assertIn('INSERT INTO \\"petstore_domain_pet\\" (\\"id\\", \\"name\\") VALUES ($1, $2) RETURNING *', generated)
        self.assertNotIn('INSERT INTO \\"petstore_domain_pet\\" (\\"id\\", \\"revision\\"', generated)
        self.assertIn('"bind":"pet"', generated)

    def test_rejects_direct_revision_assignment_on_create(self) -> None:
        with self.assertRaisesRegex(
            PostgresTransactionGeneratorError,
            "transaction create must not assign concurrency token 'revision' directly",
        ):
            generate_postgres_transactions(_create_ir(assign_revision=True))

    def test_is_deterministic_across_declaration_order(self) -> None:
        ir = _base_ir()
        reversed_ir = {**ir, "declarations": list(reversed(ir["declarations"]))}
        self.assertEqual(generate_postgres_transactions(ir), generate_postgres_transactions(reversed_ir))

    def test_rejects_missing_expected_revision_for_concurrent_update(self) -> None:
        with self.assertRaisesRegex(PostgresTransactionGeneratorError, "requires expectedRevision"):
            generate_postgres_transactions(_base_ir(expected=False))

    def test_rejects_isolation_not_declared_by_resource(self) -> None:
        ir = _base_ir(isolation="serializable")
        ir["system"]["resources"][0]["transactionIsolation"] = ["readCommitted"]
        with self.assertRaisesRegex(PostgresTransactionGeneratorError, "does not declare transaction isolation"):
            generate_postgres_transactions(ir)

    def test_integrates_transactional_publish_inside_existing_boundary(self) -> None:
        generated = generate_postgres_transactions(_base_ir(include_publish=True))
        self.assertIn('"kind":"publish"', generated)
        self.assertIn('INSERT INTO \\"aidl_outbox\\"', generated)
        self.assertIn('if (kind === "publish")', generated)
        self.assertIn('await client.query("BEGIN")', generated)
        self.assertIn('await client.query("COMMIT")', generated)

    def test_rejects_unsupported_ir_version(self) -> None:
        ir = _base_ir()
        ir["irVersion"] = "0.2.0"
        with self.assertRaisesRegex(PostgresTransactionGeneratorError, "unsupported canonical IR version"):
            generate_postgres_transactions(ir)


if __name__ == "__main__":
    unittest.main()
