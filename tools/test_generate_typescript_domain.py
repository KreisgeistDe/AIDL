from __future__ import annotations

import unittest

from tools.generate_typescript_domain import (
    GENERATED_DOMAIN_PATH,
    TypeScriptDomainGeneratorError,
    generate_typescript_domain,
    generate_typescript_domain_files,
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


def _field(name: str, type_ref: dict[str, object], required: bool = True) -> dict[str, object]:
    return {
        "name": name,
        "type": type_ref,
        "required": required,
        "mutable": False,
        "sensitive": False,
        "generated": False,
    }


class TypeScriptDomainGeneratorTest(unittest.TestCase):
    def test_generates_supported_domain_declarations_from_ir_only(self) -> None:
        pet = {
            **_identity("entity", "Pet"),
            "fields": [
                _field("id", {"kind": "scalar", "name": "uuid"}),
                _field("name", {"kind": "scalar", "name": "string"}),
                _field(
                    "tag",
                    {"kind": "nullable", "element": {"kind": "scalar", "name": "string"}},
                    required=False,
                ),
            ],
            "identityFields": ["id"],
        }
        owner = {
            **_identity("value", "Owner"),
            "fields": [
                _field(
                    "pets",
                    {
                        "kind": "list",
                        "element": {
                            "kind": "named",
                            "declarationId": "petstore.domain.Pet@1",
                            "fqn": "petstore.domain.Pet",
                            "typeArguments": [],
                        },
                    },
                )
            ],
        }
        status = {**_identity("enum", "PetStatus"), "values": ["available", "sold"]}
        label = {
            **_identity("alias", "PetLabel"),
            "target": {"kind": "scalar", "name": "string"},
        }
        pet_id = {
            **_identity("opaque", "PetId"),
            "representation": {"kind": "scalar", "name": "uuid"},
        }
        view = {
            **_identity("view", "PetSummary"),
            "sourceEntityId": "petstore.domain.Pet@1",
            "fields": [
                {
                    "name": "id",
                    "type": {"kind": "scalar", "name": "uuid"},
                    "required": True,
                }
            ],
        }
        ir = {
            "irVersion": "0.3.0",
            "declarations": [
                {**_identity("query", "GetPet"), "input": {}, "output": {}},
                owner,
                pet,
                status,
                label,
                pet_id,
                view,
            ],
        }

        generated = generate_typescript_domain(ir)

        self.assertEqual(
            generated,
            "// Generated from canonical AIDL IR by the M4 TypeScript domain generator.\n"
            "\n"
            "// M4-02 domain declarations only; runtime behavior is intentionally absent.\n"
            "\n"
            "export interface Owner {\n"
            "  readonly pets: ReadonlyArray<Pet>;\n"
            "}\n"
            "\n"
            "export interface Pet {\n"
            "  readonly id: string;\n"
            "  readonly name: string;\n"
            "  readonly tag?: string | null;\n"
            "}\n"
            "\n"
            "export type PetId = string & { readonly __aidlOpaque: \"petstore.domain.PetId\" };\n"
            "\n"
            "export type PetLabel = string;\n"
            "\n"
            "export type PetStatus = \"available\" | \"sold\";\n"
            "\n"
            "export interface PetSummary {\n"
            "  readonly id: string;\n"
            "}\n",
        )
        self.assertNotIn("GetPet", generated)
        self.assertEqual(
            generate_typescript_domain_files(ir),
            {GENERATED_DOMAIN_PATH: generated},
        )
        self.assertEqual(GENERATED_DOMAIN_PATH, "generated/domain.ts")

    def test_output_is_deterministic_across_declaration_input_order(self) -> None:
        first = {**_identity("alias", "A"), "target": {"kind": "scalar", "name": "string"}}
        second = {**_identity("alias", "B"), "target": {"kind": "scalar", "name": "int"}}
        left = generate_typescript_domain({"irVersion": "0.3.0", "declarations": [second, first]})
        right = generate_typescript_domain({"irVersion": "0.3.0", "declarations": [first, second]})
        self.assertEqual(left, right)
        self.assertLess(left.index("export type A"), left.index("export type B"))

    def test_maps_collections_records_refs_and_bytes_without_runtime_dependencies(self) -> None:
        pet = {
            **_identity("entity", "Pet"),
            "fields": [_field("id", {"kind": "scalar", "name": "uuid"})],
            "identityFields": ["id"],
        }
        holder = {
            **_identity("value", "Holder"),
            "fields": [
                _field(
                    "pet",
                    {
                        "kind": "ref",
                        "entityId": "petstore.domain.Pet@1",
                        "entityFqn": "petstore.domain.Pet",
                        "ownerServiceId": "petstore.PetService@1",
                    },
                ),
                _field("payload", {"kind": "scalar", "name": "bytes"}),
                _field(
                    "labels",
                    {
                        "kind": "map",
                        "key": {"kind": "scalar", "name": "string"},
                        "value": {"kind": "set", "element": {"kind": "scalar", "name": "string"}},
                    },
                ),
                _field(
                    "meta",
                    {
                        "kind": "record",
                        "fields": [
                            {
                                "name": "createdAt",
                                "type": {"kind": "scalar", "name": "datetime"},
                                "required": True,
                            }
                        ],
                    },
                ),
            ],
        }
        generated = generate_typescript_domain(
            {"irVersion": "0.3.0", "declarations": [holder, pet]}
        )
        self.assertIn("readonly pet: Pet;", generated)
        self.assertIn("readonly payload: Uint8Array;", generated)
        self.assertIn("ReadonlyMap<string, ReadonlySet<string>>", generated)
        self.assertIn("{ readonly createdAt: string }", generated)
        self.assertNotIn("Fastify", generated)
        self.assertNotIn("PostgreSQL", generated)

    def test_rejects_noncanonical_version_and_unsupported_external_named_type(self) -> None:
        with self.assertRaisesRegex(TypeScriptDomainGeneratorError, "unsupported canonical IR version"):
            generate_typescript_domain({"irVersion": "0.2.0", "declarations": []})

        declaration = {
            **_identity("alias", "External"),
            "target": {
                "kind": "named",
                "declarationId": "aidl.std.Unknown@1",
                "fqn": "aidl.std.Unknown",
                "typeArguments": [],
            },
        }
        with self.assertRaisesRegex(TypeScriptDomainGeneratorError, "outside the M4-02 domain generator boundary"):
            generate_typescript_domain({"irVersion": "0.3.0", "declarations": [declaration]})

    def test_rejects_type_script_symbol_collisions(self) -> None:
        one = {**_identity("alias", "Thing", "one"), "target": {"kind": "scalar", "name": "string"}}
        two = {**_identity("alias", "Thing", "two"), "target": {"kind": "scalar", "name": "string"}}
        with self.assertRaisesRegex(TypeScriptDomainGeneratorError, "collide on TypeScript symbol"):
            generate_typescript_domain({"irVersion": "0.3.0", "declarations": [one, two]})


if __name__ == "__main__":
    unittest.main()
