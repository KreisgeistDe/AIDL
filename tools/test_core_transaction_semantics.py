from __future__ import annotations

import copy
import unittest

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.generate_postgres_transactions import (
    PostgresTransactionGeneratorError,
    generate_postgres_transactions,
)
from tools.m4_petstore import SOURCE


class CoreTransactionSemanticsTest(unittest.TestCase):
    def _ir(self) -> dict:
        analysis = load_compiler_analysis([SOURCE])
        errors = [
            item.to_json()
            for item in analysis.diagnostics
            if item.severity == CompilerDiagnosticSeverity.ERROR
        ]
        self.assertEqual([], errors)
        return build_canonical_ir(analysis)

    def test_transaction_ir_preserves_resource_owner_and_outbox_publish(self) -> None:
        ir = self._ir()
        mutation = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "mutation" and item.get("name") == "createPet"
        )
        root = mutation["rootEffect"]
        self.assertEqual("transaction", root["kind"])

        resource_id = root["resourceId"]
        resources = {
            item["declarationId"]: item
            for item in ir["system"]["resources"]
        }
        self.assertIn(resource_id, resources)
        self.assertEqual("sql", resources[resource_id]["resourceKind"])

        publishes = [step for step in root["steps"] if step.get("kind") == "publish"]
        self.assertEqual(1, len(publishes))
        self.assertEqual("outbox", publishes[0]["via"])
        self.assertTrue(publishes[0]["eventId"])
        self.assertTrue(publishes[0]["topicId"])

    def test_postgres_generator_consumes_same_resource_and_outbox_in_one_transaction(self) -> None:
        ir = self._ir()
        mutation = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "mutation" and item.get("name") == "createPet"
        )
        root = mutation["rootEffect"]
        generated = generate_postgres_transactions(ir)

        self.assertIn(f'"resourceId":"{root["resourceId"]}"', generated)
        self.assertIn('"kind":"publish"', generated)
        self.assertIn('await client.query("BEGIN")', generated)
        self.assertIn('await client.query("COMMIT")', generated)
        self.assertLess(
            generated.index('if (kind === "publish")'),
            generated.index('await client.query("COMMIT")'),
        )

    def test_generator_rejects_unresolved_transaction_resource(self) -> None:
        ir = self._ir()
        candidate = copy.deepcopy(ir)
        mutation = next(
            item
            for item in candidate["declarations"]
            if item.get("kind") == "mutation" and item.get("name") == "createPet"
        )
        mutation["rootEffect"]["resourceId"] = "missing.resource@1"

        with self.assertRaisesRegex(
            PostgresTransactionGeneratorError,
            "transaction resource 'missing.resource@1' is unresolved",
        ):
            generate_postgres_transactions(candidate)

    def test_generator_rejects_non_outbox_transaction_publish(self) -> None:
        ir = self._ir()
        candidate = copy.deepcopy(ir)
        mutation = next(
            item
            for item in candidate["declarations"]
            if item.get("kind") == "mutation" and item.get("name") == "createPet"
        )
        publish = next(
            step
            for step in mutation["rootEffect"]["steps"]
            if step.get("kind") == "publish"
        )
        publish["via"] = "direct"

        with self.assertRaisesRegex(
            PostgresTransactionGeneratorError,
            "transaction publish must use canonical via=outbox",
        ):
            generate_postgres_transactions(candidate)


if __name__ == "__main__":
    unittest.main()
