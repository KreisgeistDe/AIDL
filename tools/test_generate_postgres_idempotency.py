from __future__ import annotations

import json
import unittest

from tools.generate_postgres_idempotency import (
    GENERATED_IDEMPOTENCY_PATH,
    GENERATED_MIGRATION_PATH,
    PostgresIdempotencyGeneratorError,
    generate_postgres_idempotency_files,
)


def _identity(kind: str, name: str, module: str = "petstore.operations") -> dict[str, object]:
    fqn = f"{module}.{name}"
    return {
        "kind": kind,
        "declarationId": f"{fqn}@1",
        "fqn": fqn,
        "name": name,
        "ownerModule": module,
        "semanticHash": "sha256:" + "0" * 64,
    }


def _mutation(name: str = "updatePet") -> dict[str, object]:
    mutation = {
        **_identity("mutation", name),
        "idempotency": {
            "key": {"kind": "symbol", "path": ["input", "operationId"]},
            "scope": {"kind": "literal", "value": "mutation"},
            "retentionMs": 86_400_000,
        },
        "rootEffect": {
            "kind": "transaction",
            "resourceId": "petstore.system.PetstoreDb@1",
            "isolation": "readCommitted",
            "steps": [],
            "result": {"kind": "literal", "value": None},
        },
    }
    return mutation


def _ir(mutations: list[dict[str, object]] | None = None) -> dict[str, object]:
    mutations = mutations or [_mutation()]
    mutation_ids = [str(item["declarationId"]) for item in mutations]
    return {
        "irVersion": "0.3.0",
        "declarations": mutations,
        "system": {
            "resources": [
                {
                    "declarationId": "petstore.system.PetstoreDb@1",
                    "fqn": "petstore.system.PetstoreDb",
                    "resourceKind": "sql",
                    "transactionIsolation": ["readCommitted", "serializable"],
                }
            ],
            "services": [
                {
                    "declarationId": "petstore.system.PetService@1",
                    "fqn": "petstore.system.PetService",
                    "exposes": mutation_ids,
                    "reliability": {"idempotencyStoreId": "petstore.system.PetstoreDb@1"},
                }
            ],
        },
    }


class PostgresIdempotencyGeneratorTest(unittest.TestCase):
    def test_generates_deterministic_runtime_and_migration(self) -> None:
        first = _mutation("updatePet")
        second = _mutation("createPet")
        files = generate_postgres_idempotency_files(_ir([first, second]))
        reversed_files = generate_postgres_idempotency_files(_ir([second, first]))

        self.assertEqual(files, reversed_files)
        self.assertEqual(set(files), {GENERATED_IDEMPOTENCY_PATH, GENERATED_MIGRATION_PATH})
        runtime = files[GENERATED_IDEMPOTENCY_PATH]
        migration = files[GENERATED_MIGRATION_PATH]
        self.assertIn('"operationId":"petstore.operations.createPet@1"', runtime)
        self.assertIn('"retentionMs":86400000', runtime)
        self.assertIn('SELECT \\"state\\", \\"result\\" FROM \\"aidl_idempotency\\"', runtime)
        self.assertIn('ON CONFLICT (\\"operation_id\\", \\"scope\\", \\"key\\") DO NOTHING', runtime)
        self.assertIn('export async function executeCreatePetIdempotent', runtime)
        self.assertIn('CREATE TABLE IF NOT EXISTS "aidl_idempotency"', migration)
        self.assertIn('PRIMARY KEY ("operation_id", "scope", "key")', migration)
        self.assertNotIn("outbox", runtime.lower())

    def test_serializes_sql_literals_without_changing_sql_semantics(self) -> None:
        runtime = generate_postgres_idempotency_files(_ir())[GENERATED_IDEMPOTENCY_PATH]
        expected_sql = [
            'INSERT INTO "aidl_idempotency" ("operation_id", "scope", "key", "state", "expires_at") VALUES ($1, $2, $3, \'running\', CURRENT_TIMESTAMP + ($4 * INTERVAL \'1 millisecond\')) ON CONFLICT ("operation_id", "scope", "key") DO NOTHING RETURNING "operation_id"',
            'UPDATE "aidl_idempotency" SET "state" = \'completed\', "result" = $4::jsonb WHERE "operation_id" = $1 AND "scope" = $2 AND "key" = $3',
            'DELETE FROM "aidl_idempotency" WHERE "operation_id" = $1 AND "scope" = $2 AND "key" = $3 AND "state" = \'running\'',
        ]
        for sql in expected_sql:
            self.assertIn(json.dumps(sql, ensure_ascii=False), runtime)
        self.assertIn("'running'", runtime)
        self.assertIn("'completed'", runtime)
        self.assertIn("INTERVAL '1 millisecond'", runtime)

    def test_requires_exactly_one_exposing_service_and_sql_store(self) -> None:
        ir = _ir()
        ir["system"]["services"] = []  # type: ignore[index]
        with self.assertRaisesRegex(PostgresIdempotencyGeneratorError, "exactly one service"):
            generate_postgres_idempotency_files(ir)

        ir = _ir()
        ir["system"]["resources"][0]["resourceKind"] = "kv"  # type: ignore[index]
        with self.assertRaisesRegex(PostgresIdempotencyGeneratorError, "is not SQL"):
            generate_postgres_idempotency_files(ir)

    def test_rejects_cross_resource_idempotency_and_non_input_key(self) -> None:
        ir = _ir()
        ir["system"]["resources"].append(  # type: ignore[index]
            {
                "declarationId": "petstore.system.IdempotencyDb@1",
                "fqn": "petstore.system.IdempotencyDb",
                "resourceKind": "sql",
                "transactionIsolation": ["readCommitted"],
            }
        )
        ir["system"]["services"][0]["reliability"]["idempotencyStoreId"] = "petstore.system.IdempotencyDb@1"  # type: ignore[index]
        with self.assertRaisesRegex(PostgresIdempotencyGeneratorError, "cross-resource idempotency"):
            generate_postgres_idempotency_files(ir)

        mutation = _mutation()
        mutation["idempotency"]["key"] = {"kind": "symbol", "path": ["request", "operationId"]}  # type: ignore[index]
        with self.assertRaisesRegex(PostgresIdempotencyGeneratorError, "rooted at input"):
            generate_postgres_idempotency_files(_ir([mutation]))

    def test_rejects_invalid_retention_and_unsupported_ir_version(self) -> None:
        mutation = _mutation()
        mutation["idempotency"]["retentionMs"] = 0  # type: ignore[index]
        with self.assertRaisesRegex(PostgresIdempotencyGeneratorError, "invalid idempotency retentionMs"):
            generate_postgres_idempotency_files(_ir([mutation]))

        ir = _ir()
        ir["irVersion"] = "0.2.0"
        with self.assertRaisesRegex(PostgresIdempotencyGeneratorError, "unsupported canonical IR version"):
            generate_postgres_idempotency_files(ir)


if __name__ == "__main__":
    unittest.main()
