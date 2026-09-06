from __future__ import annotations

import json
import unittest

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.generate_m4 import generate_m4_files
from tools.generated_ownership import validate_generated_file
from tools.ir_plan import build_plan
from tools.m4_petstore import APP_ROOT, SOURCE


class M4PetstoreTest(unittest.TestCase):
    def test_petstore_source_is_checkable_plannable_and_generatable(self) -> None:
        analysis = load_compiler_analysis([SOURCE])
        errors = [item.to_json() for item in analysis.diagnostics if item.severity == CompilerDiagnosticSeverity.ERROR]
        self.assertEqual([], errors)
        ir = build_canonical_ir(analysis)
        self.assertEqual("0.3.0", ir["irVersion"])
        plan = build_plan(ir)
        self.assertTrue(plan)

        first = generate_m4_files(ir)
        second = generate_m4_files(build_canonical_ir(load_compiler_analysis([SOURCE])))
        self.assertEqual(first, second)
        self.assertEqual(
            set(first),
            {
                "generated/domain.ts",
                "generated/api.ts",
                "generated/schema.sql",
                "generated/migrations/0001_initial.sql",
                "generated/transactions.ts",
                "generated/idempotency.ts",
                "generated/migrations/0002_idempotency.sql",
                "generated/outbox.ts",
                "generated/migrations/0003_outbox.sql",
            },
        )
        for path, content in first.items():
            validate_generated_file(path, content)

    def test_node_manifest_matches_m4_stack_contract(self) -> None:
        package = json.loads((APP_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual("npm@10.9.2", package["packageManager"])
        self.assertEqual("5.6.0", package["dependencies"]["fastify"])
        self.assertEqual("8.16.3", package["dependencies"]["pg"])
        self.assertEqual("5.9.2", package["devDependencies"]["typescript"])
        self.assertTrue((APP_ROOT / "package-lock.json").exists())
        self.assertEqual("NodeNext", json.loads((APP_ROOT / "tsconfig.json").read_text(encoding="utf-8"))["compilerOptions"]["module"])
        self.assertTrue(json.loads((APP_ROOT / "tsconfig.json").read_text(encoding="utf-8"))["compilerOptions"]["strict"])


if __name__ == "__main__":
    unittest.main()
