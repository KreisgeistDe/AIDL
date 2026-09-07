from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.m4_petstore import SOURCE


class CoreEntityOwnershipSemanticsTest(unittest.TestCase):
    def _ir_with_owner_local_ref(self) -> dict:
        text = SOURCE.read_text(encoding="utf-8")
        text = text.replace(
            "export entity RunnablePet {\n",
            "export entity RunnableCustomer {\n"
            "  id: uuid primary immutable\n"
            "}\n\n"
            "export entity RunnablePet {\n",
            1,
        )
        text = text.replace(
            "  name: string(1..80) required mutable\n}\n\nexport event RunnablePetCreated",
            "  name: string(1..80) required mutable\n"
            "  customer: ref RunnableCustomer required\n"
            "}\n\nexport event RunnablePetCreated",
            1,
        )
        text = text.replace(
            "  owns [RunnablePet]\n",
            "  owns [RunnablePet, RunnableCustomer]\n",
            1,
        )

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            analysis = load_compiler_analysis([source])
            errors = [
                item.to_json()
                for item in analysis.diagnostics
                if item.severity == CompilerDiagnosticSeverity.ERROR
            ]
            self.assertEqual([], errors)
            return build_canonical_ir(analysis)

    def test_ir_preserves_single_owner_and_owner_local_ref_boundary(self) -> None:
        ir = self._ir_with_owner_local_ref()
        service = next(
            item for item in ir["system"]["services"] if item["name"] == "PetstoreService"
        )
        pet = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "entity" and item.get("name") == "RunnablePet"
        )
        customer = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "entity" and item.get("name") == "RunnableCustomer"
        )

        self.assertEqual(
            sorted([pet["declarationId"], customer["declarationId"]]),
            sorted(service["owns"]),
        )
        customer_field = next(field for field in pet["fields"] if field["name"] == "customer")
        self.assertEqual("ref", customer_field["type"]["kind"])
        self.assertEqual(customer["declarationId"], customer_field["type"]["entityId"])
        self.assertEqual(service["declarationId"], customer_field["type"]["ownerServiceId"])

    def test_ir_preserves_owner_local_persistent_access_relation(self) -> None:
        ir = self._ir_with_owner_local_ref()
        service = next(
            item for item in ir["system"]["services"] if item["name"] == "PetstoreService"
        )
        mutation = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "mutation" and item.get("name") == "createPet"
        )
        self.assertIn(mutation["declarationId"], service["exposes"])
        writes = [
            step
            for step in mutation["rootEffect"]["steps"]
            if step.get("kind") == "write"
        ]
        self.assertEqual(1, len(writes))
        self.assertIn(writes[0]["entityId"], service["owns"])


if __name__ == "__main__":
    unittest.main()
