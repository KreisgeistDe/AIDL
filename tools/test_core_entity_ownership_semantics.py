from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.m4_petstore import SOURCE


class CoreEntityOwnershipSemanticsTest(unittest.TestCase):
    def _analysis(self, text: str):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        source = Path(directory.name) / "app.aidl"
        source.write_text(text, encoding="utf-8")
        return load_compiler_analysis([source])

    def _owner_local_ref_source(self) -> str:
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
        return text.replace(
            "  owns [RunnablePet]\n",
            "  owns [RunnablePet, RunnableCustomer]\n",
            1,
        )

    def _ir_with_owner_local_ref(self) -> dict:
        analysis = self._analysis(self._owner_local_ref_source())
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

    def test_single_owner_violation_is_rejected_before_ir_materialization(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").replace(
            "  owns [RunnablePet]\n", "  owns []\n", 1
        )
        analysis = self._analysis(text)
        self.assertIn("AIDL-DIST400", [item.code.value for item in analysis.diagnostics])

    def test_cross_service_ref_is_rejected_before_ir_materialization(self) -> None:
        text = self._owner_local_ref_source().replace(
            "  owns [RunnablePet, RunnableCustomer]\n",
            "  owns [RunnablePet]\n",
            1,
        )
        text = text.replace(
            "export system PetstoreSystem {\n",
            "export service CustomerService {\n"
            "  owns [RunnableCustomer]\n"
            "  uses []\n"
            "  exposes []\n"
            "  runs []\n"
            "}\n\n"
            "export system PetstoreSystem {\n",
            1,
        ).replace(
            "  services [PetstoreService]\n",
            "  services [PetstoreService, CustomerService]\n",
            1,
        )
        analysis = self._analysis(text)
        self.assertIn("AIDL-DIST401", [item.code.value for item in analysis.diagnostics])

    def test_foreign_owner_persistent_access_is_rejected_before_ir_materialization(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").replace(
            "  owns [RunnablePet]\n", "  owns []\n", 1
        )
        text = text.replace(
            "export system PetstoreSystem {\n",
            "export service ForeignPetService {\n"
            "  owns [RunnablePet]\n"
            "  uses []\n"
            "  exposes []\n"
            "  runs []\n"
            "}\n\n"
            "export system PetstoreSystem {\n",
            1,
        ).replace(
            "  services [PetstoreService]\n",
            "  services [PetstoreService, ForeignPetService]\n",
            1,
        )
        analysis = self._analysis(text)
        self.assertIn("AIDL-DIST402", [item.code.value for item in analysis.diagnostics])


if __name__ == "__main__":
    unittest.main()
