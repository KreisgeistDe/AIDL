from __future__ import annotations

import unittest

from tools.generate_fastify_api import FastifyApiGeneratorError, generate_fastify_api, generate_fastify_api_files


def _identity(kind: str, name: str, module: str = "petstore.api") -> dict[str, object]:
    fqn = f"{module}.{name}"
    return {
        "kind": kind,
        "declarationId": f"{fqn}@1",
        "fqn": fqn,
        "name": name,
        "ownerModule": module,
        "semanticHash": "sha256:" + "0" * 64,
    }


def _named(name: str, module: str = "petstore.domain") -> dict[str, object]:
    fqn = f"{module}.{name}"
    return {"kind": "named", "declarationId": f"{fqn}@1", "fqn": fqn, "typeArguments": []}


def _record(**fields: dict[str, object]) -> dict[str, object]:
    return {
        "kind": "record",
        "fields": [
            {"name": name, "type": type_ref, "required": True}
            for name, type_ref in fields.items()
        ],
    }


def _fixture() -> dict[str, object]:
    pet = {
        **_identity("entity", "Pet", "petstore.domain"),
        "fields": [
            {
                "name": "id",
                "type": {"kind": "scalar", "name": "uuid"},
                "required": True,
                "mutable": False,
                "sensitive": False,
                "generated": False,
            }
        ],
        "identityFields": ["id"],
    }
    get_pet = {
        **_identity("query", "getPet"),
        "input": _record(id={"kind": "scalar", "name": "uuid"}),
        "output": _named("Pet"),
        "auth": {"mode": "authenticated"},
        "errorIds": ["petstore.api.NotFound@1"],
        "read": {"entityId": "petstore.domain.Pet@1", "steps": []},
        "consistency": "strong",
    }
    create_pet = {
        **_identity("mutation", "createPet"),
        "input": _record(pet=_named("Pet")),
        "output": _named("Pet"),
        "auth": {"mode": "authenticated"},
        "allow": {"kind": "literal", "value": True},
        "errorIds": [],
        "idempotency": {
            "key": {"kind": "literal", "value": "x"},
            "scope": {"kind": "literal", "value": "y"},
            "retentionMs": 1000,
        },
        "rootEffect": {
            "kind": "transaction",
            "resourceId": "petstore.db.Postgres@1",
            "isolation": "readCommitted",
            "steps": [],
            "result": {"kind": "literal", "value": None},
        },
    }
    api = {
        **_identity("api", "PetstoreApi"),
        "transport": "rest",
        "majorVersion": 1,
        "basePath": "/api/v1",
        "operations": [
            {"kind": "query", "operationId": "petstore.api.getPet@1"},
            {"kind": "mutation", "operationId": "petstore.api.createPet@1"},
        ],
        "auth": {"mode": "inherit"},
        "errorEncoding": "problemDetails",
        "compatibility": "backward",
    }
    return {"irVersion": "0.3.0", "declarations": [create_pet, pet, api, get_pet]}


class FastifyApiGeneratorTest(unittest.TestCase):
    def test_generates_fastify_contracts_and_routes_from_canonical_ir(self) -> None:
        generated = generate_fastify_api(_fixture())

        self.assertIn('import type { FastifyInstance } from "fastify";', generated)
        self.assertIn('import type { Pet } from "./domain.js";', generated)
        self.assertIn("export type getPetInput = { readonly id: string };", generated)
        self.assertIn("export type getPetOutput = Pet;", generated)
        self.assertIn("export type createPetInput = { readonly pet: Pet };", generated)
        self.assertIn('app.get("/api/v1/getPet"', generated)
        self.assertIn('app.post("/api/v1/createPet"', generated)
        self.assertIn("handlers.getPet(request.query as getPetInput)", generated)
        self.assertIn("handlers.createPet(request.body as createPetInput)", generated)
        self.assertIn('"authMode":"inherit"', generated)
        self.assertIn('"errorIds":["petstore.api.NotFound@1"]', generated)
        self.assertNotIn("PostgreSQL", generated)
        self.assertNotIn("idempotency", generated)
        self.assertEqual(list(generate_fastify_api_files(_fixture())), ["generated/api.ts"])

    def test_output_is_deterministic_across_declaration_input_order(self) -> None:
        left = _fixture()
        right = _fixture()
        right["declarations"] = list(reversed(right["declarations"]))
        self.assertEqual(generate_fastify_api(left), generate_fastify_api(right))

    def test_generates_only_explicitly_exposed_operations(self) -> None:
        ir = _fixture()
        hidden = {
            **_identity("query", "hiddenQuery"),
            "input": _record(),
            "output": {"kind": "scalar", "name": "string"},
            "auth": {"mode": "authenticated"},
            "errorIds": [],
            "read": {"entityId": "petstore.domain.Pet@1", "steps": []},
            "consistency": "strong",
        }
        ir["declarations"].append(hidden)
        generated = generate_fastify_api(ir)
        self.assertNotIn("hiddenQuery", generated)

    def test_rejects_non_rest_api_and_missing_operation(self) -> None:
        ir = _fixture()
        api = next(item for item in ir["declarations"] if item.get("kind") == "api")
        api["transport"] = "graphql"
        with self.assertRaisesRegex(FastifyApiGeneratorError, "unsupported transport"):
            generate_fastify_api(ir)

        ir = _fixture()
        api = next(item for item in ir["declarations"] if item.get("kind") == "api")
        api["operations"] = [{"kind": "query", "operationId": "petstore.api.missing@1"}]
        with self.assertRaisesRegex(FastifyApiGeneratorError, "not present in canonical IR"):
            generate_fastify_api(ir)

    def test_rejects_duplicate_generated_routes(self) -> None:
        ir = _fixture()
        api = next(item for item in ir["declarations"] if item.get("kind") == "api")
        api["operations"].append({"kind": "query", "operationId": "petstore.api.getPet@1"})
        with self.assertRaisesRegex(FastifyApiGeneratorError, "duplicate generated route"):
            generate_fastify_api(ir)

    def test_reuses_m4_domain_type_failure_boundary(self) -> None:
        ir = _fixture()
        operation = next(item for item in ir["declarations"] if item.get("kind") == "query")
        operation["output"] = {
            "kind": "named",
            "declarationId": "aidl.std.Unknown@1",
            "fqn": "aidl.std.Unknown",
            "typeArguments": [],
        }
        with self.assertRaisesRegex(FastifyApiGeneratorError, "outside the M4-02 domain generator boundary"):
            generate_fastify_api(ir)


if __name__ == "__main__":
    unittest.main()
