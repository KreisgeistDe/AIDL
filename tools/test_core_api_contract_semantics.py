from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.m4_petstore import SOURCE


class CoreApiContractSemanticsTest(unittest.TestCase):
    def test_ir_preserves_valid_api_exposure_version_and_compatibility(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        original_api = (
            "export api PetstoreApi {\n"
            "  transport rest\n"
            "  version 1\n"
            "  operations [mutation createPet]\n"
            "  auth inherit\n"
            "  errors problemDetails\n"
            "  compatibility backward\n"
            "  rateLimit principal 300 per 1m burst 50\n"
            "}\n"
        )
        varied_api = (
            "export api PetstoreApi {\n"
            "  transport rpc\n"
            "  version 2\n"
            "  operations [mutation createPet]\n"
            "  auth inherit\n"
            "  errors problemDetails\n"
            "  compatibility full\n"
            "  rateLimit principal 300 per 1m burst 50\n"
            "}\n"
        )
        self.assertIn(original_api, text)
        text = text.replace(original_api, varied_api, 1)

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
            ir = build_canonical_ir(analysis)

        api = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "api" and item.get("name") == "PetstoreApi"
        )
        mutation = next(
            item
            for item in ir["declarations"]
            if item.get("kind") == "mutation" and item.get("name") == "createPet"
        )
        self.assertEqual("rpc", api["transport"])
        self.assertEqual(2, api["majorVersion"])
        self.assertEqual("full", api["compatibility"])
        self.assertEqual(
            [{"kind": "mutation", "operationId": mutation["declarationId"]}],
            api["operations"],
        )

    def test_invalid_api_contract_is_rejected_before_ir(self) -> None:
        source_text = """module example.api
query ListPets {
}
api BrokenApi {
  transport websocket
  version 0
  operations [query Missing]
  compatibility rolling
}
"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "api.aidl"
            source.write_text(source_text, encoding="utf-8")
            analysis = load_compiler_analysis([source])

        diagnostics = [item for item in analysis.diagnostics if item.code == "AIDL-DIST412"]
        self.assertEqual(4, len(diagnostics))
        self.assertEqual(
            [
                "api 'example.api.BrokenApi' transport must be one of rest, rpc, graphql; found 'websocket'",
                "api 'example.api.BrokenApi' version must be a positive major integer; found '0'",
                "api 'example.api.BrokenApi' operation query 'Missing' must resolve uniquely; found 0 matching query declarations",
                "api 'example.api.BrokenApi' compatibility must be one of none, backward, forward, full; found 'rolling'",
            ],
            [item.message for item in diagnostics],
        )
        self.assertEqual(
            [(5, 3), (6, 3), (7, 3), (8, 3)],
            [(item.location.line, item.location.column) for item in diagnostics],
        )


if __name__ == "__main__":
    unittest.main()
