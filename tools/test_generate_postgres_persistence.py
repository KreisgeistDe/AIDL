from __future__ import annotations

import unittest

from tools.generate_postgres_persistence import (
    GENERATED_MIGRATION_PATH,
    GENERATED_SCHEMA_PATH,
    PostgresPersistenceGeneratorError,
    generate_postgres_persistence_files,
    generate_postgres_schema,
)


def _identity(kind: str, name: str, module: str = "petstore.domain") -> dict[str, object]:
    fqn = f"{module}.{name}"
    return {
        "kind": kind,
        "declarationId": f"{fqn}@1",
        "fqn": fqn,
        "name": name,
        "ownerModule": module,
        "semanticHash": "sha256:" + "0" * 64,
    }


def _field(name: str, type_ref: dict[str, object], required: bool = True, **extra: object) -> dict[str, object]:
    return {
        "name": name,
        "type": type_ref,
        "required": required,
        "mutable": False,
        "sensitive": False,
        "generated": False,
        **extra,
    }


class PostgresPersistenceGeneratorTest(unittest.TestCase):
    def test_generates_deterministic_schema_and_initial_migration(self) -> None:
        status = {**_identity("enum", "PetStatus"), "values": ["available", "adopted"]}
        shelter = {
            **_identity("entity", "Shelter"),
            "fields": [
                _field("id", {"kind": "scalar", "name": "uuid"}, primary=True, generated=True),
                _field("name", {"kind": "scalar", "name": "string", "constraints": {"minLength": 1, "maxLength": 120}}),
            ],
            "identityFields": ["id"],
        }
        pet = {
            **_identity("entity", "Pet"),
            "fields": [
                _field("id", {"kind": "scalar", "name": "uuid"}, primary=True, generated=True),
                _field("revision", {"kind": "scalar", "name": "revision"}, generated=True, concurrencyToken=True),
                _field("ageMonths", {"kind": "scalar", "name": "int", "constraints": {"minimum": 0, "maximum": 480}}),
                _field(
                    "status",
                    {
                        "kind": "named",
                        "declarationId": "petstore.domain.PetStatus@1",
                        "fqn": "petstore.domain.PetStatus",
                        "typeArguments": [],
                    },
                ),
                _field(
                    "shelter",
                    {
                        "kind": "ref",
                        "entityId": "petstore.domain.Shelter@1",
                        "entityFqn": "petstore.domain.Shelter",
                        "ownerServiceId": "petstore.PetService@1",
                    },
                    onDelete="restrict",
                ),
                _field(
                    "adoptedAt",
                    {"kind": "nullable", "element": {"kind": "scalar", "name": "datetime"}},
                    required=False,
                ),
            ],
            "identityFields": ["id"],
        }
        ir = {"irVersion": "0.3.0", "declarations": [pet, status, shelter]}

        schema = generate_postgres_schema(ir)
        files = generate_postgres_persistence_files(ir)

        self.assertEqual(schema, generate_postgres_schema({"irVersion": "0.3.0", "declarations": [shelter, status, pet]}))
        self.assertEqual(set(files), {GENERATED_SCHEMA_PATH, GENERATED_MIGRATION_PATH})
        self.assertEqual(files[GENERATED_SCHEMA_PATH], schema)
        self.assertTrue(files[GENERATED_MIGRATION_PATH].endswith(schema))
        self.assertIn('CREATE TABLE "petstore_domain_pet"', schema)
        self.assertIn('"revision" bigint NOT NULL DEFAULT 1', schema)
        self.assertIn('"adoptedAt" timestamptz', schema)
        self.assertIn('CHECK ("ageMonths" >= 0)', schema)
        self.assertIn('CHECK ("ageMonths" <= 480)', schema)
        self.assertIn('CHECK ("status" IN (\'available\', \'adopted\'))', schema)
        self.assertIn('REFERENCES "petstore_domain_shelter" ("id") ON DELETE RESTRICT', schema)
        self.assertNotIn("BEGIN", schema)
        self.assertNotIn("FOR UPDATE", schema)

    def test_only_generated_revision_concurrency_token_gets_store_default(self) -> None:
        entity = {
            **_identity("entity", "Versioned"),
            "fields": [
                _field("id", {"kind": "scalar", "name": "uuid"}, primary=True),
                _field("revision", {"kind": "scalar", "name": "revision"}, generated=True, concurrencyToken=True),
                _field("observedRevision", {"kind": "scalar", "name": "revision"}),
            ],
            "identityFields": ["id"],
        }

        schema = generate_postgres_schema({"irVersion": "0.3.0", "declarations": [entity]})

        self.assertIn('"revision" bigint NOT NULL DEFAULT 1', schema)
        self.assertIn('"observedRevision" bigint NOT NULL', schema)
        self.assertEqual(schema.count("DEFAULT 1"), 1)

    def test_resolves_alias_and_opaque_storage_representations(self) -> None:
        code = {**_identity("opaque", "PetCode"), "representation": {"kind": "scalar", "name": "string"}}
        alias = {
            **_identity("alias", "ExternalCode"),
            "target": {
                "kind": "named",
                "declarationId": "petstore.domain.PetCode@1",
                "fqn": "petstore.domain.PetCode",
                "typeArguments": [],
            },
        }
        entity = {
            **_identity("entity", "Thing"),
            "fields": [
                _field("id", {"kind": "scalar", "name": "uuid"}, primary=True),
                _field(
                    "code",
                    {
                        "kind": "named",
                        "declarationId": "petstore.domain.ExternalCode@1",
                        "fqn": "petstore.domain.ExternalCode",
                        "typeArguments": [],
                    },
                ),
            ],
            "identityFields": ["id"],
        }
        schema = generate_postgres_schema({"irVersion": "0.3.0", "declarations": [entity, alias, code]})
        self.assertIn('"code" text NOT NULL', schema)

    def test_rejects_unsupported_collection_and_record_persistence(self) -> None:
        for type_ref in (
            {"kind": "list", "element": {"kind": "scalar", "name": "string"}},
            {"kind": "record", "fields": []},
        ):
            entity = {
                **_identity("entity", "Unsupported"),
                "fields": [
                    _field("id", {"kind": "scalar", "name": "uuid"}, primary=True),
                    _field("payload", type_ref),
                ],
                "identityFields": ["id"],
            }
            with self.subTest(kind=type_ref["kind"]):
                with self.assertRaisesRegex(PostgresPersistenceGeneratorError, "outside the M4-04 PostgreSQL persistence subset"):
                    generate_postgres_schema({"irVersion": "0.3.0", "declarations": [entity]})

    def test_rejects_unsupported_ir_version_and_invalid_set_null(self) -> None:
        with self.assertRaisesRegex(PostgresPersistenceGeneratorError, "unsupported canonical IR version"):
            generate_postgres_schema({"irVersion": "0.2.0", "declarations": []})

        parent = {
            **_identity("entity", "Parent"),
            "fields": [_field("id", {"kind": "scalar", "name": "uuid"}, primary=True)],
            "identityFields": ["id"],
        }
        child = {
            **_identity("entity", "Child"),
            "fields": [
                _field("id", {"kind": "scalar", "name": "uuid"}, primary=True),
                _field(
                    "parent",
                    {
                        "kind": "ref",
                        "entityId": "petstore.domain.Parent@1",
                        "entityFqn": "petstore.domain.Parent",
                        "ownerServiceId": "petstore.Service@1",
                    },
                    onDelete="setNull",
                ),
            ],
            "identityFields": ["id"],
        }
        with self.assertRaisesRegex(PostgresPersistenceGeneratorError, "cannot use onDelete setNull while required"):
            generate_postgres_schema({"irVersion": "0.3.0", "declarations": [parent, child]})


if __name__ == "__main__":
    unittest.main()
