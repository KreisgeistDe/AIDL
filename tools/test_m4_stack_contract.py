from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "spec" / "m4-stack.json"
DOC_PATH = ROOT / "docs" / "m4-generator-runtime-stack.md"


class M4StackContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.docs = DOC_PATH.read_text(encoding="utf-8")

    def test_selected_stack_is_exact_and_narrow(self) -> None:
        self.assertEqual("1.0.0", self.contract["contractVersion"])
        self.assertEqual("examples/petstore", self.contract["fixture"])
        self.assertEqual("generated/", self.contract["generatedRoot"])
        self.assertEqual(
            {
                "name": "TypeScript",
                "version": "5.9.x",
                "moduleSystem": "ESM",
                "strict": True,
            },
            self.contract["language"],
        )
        self.assertEqual(
            {"name": "Node.js", "version": "22.x LTS", "platform": "Linux x86_64"},
            self.contract["runtime"],
        )
        self.assertEqual("REST", self.contract["api"]["transport"])
        self.assertEqual("Fastify", self.contract["api"]["framework"])
        self.assertEqual("5.x", self.contract["api"]["frameworkVersion"])
        self.assertEqual("PostgreSQL", self.contract["persistence"]["database"])
        self.assertEqual("17.x", self.contract["persistence"]["databaseVersion"])
        self.assertEqual("pg", self.contract["persistence"]["driver"])
        self.assertIsNone(self.contract["persistence"]["orm"])
        self.assertEqual("SQL", self.contract["persistence"]["migrationFormat"])

    def test_generator_boundary_preserves_ir_as_source_of_truth(self) -> None:
        boundary = self.contract["generatorBoundary"]
        self.assertEqual("canonical AIDL IR only", boundary["input"])
        self.assertFalse(boundary["reparseSource"])
        self.assertFalse(boundary["manualGeneratedEdits"])

    def test_required_and_deferred_capabilities_are_explicit(self) -> None:
        required = set(self.contract["support"]["required"])
        self.assertTrue(
            {
                "domain types and entities",
                "REST query and mutation routes",
                "PostgreSQL persistence",
                "owner-local transactions",
                "optimistic concurrency",
                "idempotency",
                "transactional outbox events",
            }.issubset(required)
        )
        deferred = set(self.contract["support"]["deferred"])
        self.assertTrue({"GraphQL generation", "RPC generation", "multi-language generators"}.issubset(deferred))

    def test_human_documentation_names_machine_contract_and_non_goals(self) -> None:
        for phrase in (
            "`spec/m4-stack.json`",
            "TypeScript 5.9.x",
            "Node.js 22.x LTS",
            "Fastify 5.x",
            "PostgreSQL 17.x",
            "canonical AIDL IR only",
            "does not add a generator command",
        ):
            self.assertIn(phrase, self.docs)


if __name__ == "__main__":
    unittest.main()
