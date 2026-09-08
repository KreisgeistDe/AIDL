from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.compiler_m1_resolution import collect_m1_resolution_diagnostics
from tools.test_aidl_ir import _MINIMAL_PROJECT


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))


class CoreModuleImportClaimModelTest(unittest.TestCase):
    def _paths(self, sources: dict[str, str]) -> list[Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        paths = []
        for name, text in sorted(sources.items()):
            path = root / name
            path.write_text(text, encoding="utf-8")
            paths.append(path)
        return paths

    def _analysis(self, sources: dict[str, str]):
        return load_compiler_analysis(self._paths(sources))

    @staticmethod
    def _errors(analysis):
        return tuple(
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.severity == CompilerDiagnosticSeverity.ERROR
        )

    @staticmethod
    def _diagnostics(analysis, code: str):
        return tuple(
            diagnostic for diagnostic in analysis.diagnostics if diagnostic.code.value == code
        )

    @staticmethod
    def _m1_diagnostics(analysis, code: str):
        return tuple(
            diagnostic
            for diagnostic in collect_m1_resolution_diagnostics(analysis.project)
            if diagnostic.code.value == code
        )

    @staticmethod
    def _declaration(document: dict, name: str) -> dict:
        return next(item for item in document["declarations"] if item.get("name") == name)

    def test_leading_modules_and_explicit_wildcard_imports_preserve_same_identity(self) -> None:
        sources = {
            "a_app.aidl": _MINIMAL_PROJECT,
            "b_types.aidl": """module example.types
export value Shared {
  id: uuid required
}
""",
            "c_explicit.aidl": """module example.explicit
import example.types.Shared
value UsesExplicit {
  shared: Shared required
}
""",
            "d_wildcard.aidl": """module example.wildcard
import example.types.*
value UsesWildcard {
  shared: Shared required
}
""",
        }
        paths = self._paths(sources)
        first_analysis = load_compiler_analysis(paths)
        second_analysis = load_compiler_analysis(paths)
        self.assertEqual([], [item.to_json() for item in self._errors(first_analysis)])
        self.assertEqual([], [item.to_json() for item in self._errors(second_analysis)])

        resolutions = {
            resolution.document.module.name: resolution
            for resolution in first_analysis.project.import_resolutions
            if resolution.document.module is not None
        }
        explicit_resolution = resolutions["example.explicit"]
        wildcard_resolution = resolutions["example.wildcard"]
        self.assertEqual("example.types.Shared", explicit_resolution.import_.name)
        self.assertEqual("example.types.*", wildcard_resolution.import_.name)
        self.assertFalse(explicit_resolution.import_.wildcard)
        self.assertTrue(wildcard_resolution.import_.wildcard)
        self.assertEqual(1, len(explicit_resolution.declarations))
        self.assertEqual(1, len(wildcard_resolution.declarations))
        self.assertEqual(
            explicit_resolution.declarations[0].fully_qualified_name,
            wildcard_resolution.declarations[0].fully_qualified_name,
        )

        first = build_canonical_ir(first_analysis)
        second = build_canonical_ir(second_analysis)
        self.assertEqual(first, second)
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        self.assertEqual((), tuple(validator.iter_errors(first)))

        shared = self._declaration(first, "Shared")
        explicit = self._declaration(first, "UsesExplicit")
        wildcard = self._declaration(first, "UsesWildcard")
        self.assertEqual("example.types", shared["ownerModule"])
        self.assertEqual("example.types.Shared", shared["fqn"])
        self.assertEqual("example.types.Shared@1", shared["declarationId"])
        self.assertEqual("example.explicit", explicit["ownerModule"])
        self.assertEqual("example.wildcard", wildcard["ownerModule"])
        explicit_type = explicit["fields"][0]["type"]
        wildcard_type = wildcard["fields"][0]["type"]
        self.assertEqual(shared["declarationId"], explicit_type["declarationId"])
        self.assertEqual(shared["declarationId"], wildcard_type["declarationId"])
        self.assertEqual(shared["fqn"], explicit_type["fqn"])
        self.assertEqual(shared["fqn"], wildcard_type["fqn"])

    def test_duplicate_and_late_module_declarations_are_source_located(self) -> None:
        cases = {
            "duplicate": (
                "module example.first\nmodule example.second\nvalue Item {\n  id: uuid required\n}\n",
                "more than once",
                (2, 1),
            ),
            "after import": (
                "import example.missing.Shared\nmodule example.late\n",
                "must appear before imports and declarations",
                (2, 1),
            ),
            "after declaration": (
                "value Before {\n  id: uuid required\n}\nmodule example.late\n",
                "must appear before imports and declarations",
                (4, 1),
            ),
        }
        for name, (source, fragment, location) in cases.items():
            with self.subTest(name=name):
                analysis = self._analysis({"case.aidl": source})
                diagnostics = self._diagnostics(analysis, "AIDL-R005")
                self.assertTrue(any(fragment in item.message for item in diagnostics))
                matching = next(item for item in diagnostics if fragment in item.message)
                self.assertEqual(location, (matching.location.line, matching.location.column))
                self.assertEqual("resolve", matching.phase)
                self.assertEqual("module", matching.subject.kind)

    def test_unresolved_explicit_and_wildcard_imports_remain_aidl_r001(self) -> None:
        cases = {
            "explicit": "module example.client\nimport missing.types.Shared\n",
            "wildcard": "module example.client\nimport missing.types.*\n",
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                analysis = self._analysis({"client.aidl": source})
                self.assertEqual(1, len(self._diagnostics(analysis, "AIDL-R001")))
                self.assertEqual((), self._diagnostics(analysis, "AIDL-R005"))
                self.assertEqual((), self._m1_diagnostics(analysis, "AIDL-R004"))

    def test_direct_and_multi_module_cycles_keep_existing_m1_diagnostic_owner(self) -> None:
        direct = self._analysis(
            {
                "self.aidl": """module cycle.self
import cycle.self.A
export value A {
  id: uuid required
}
"""
            }
        )
        direct_cycle = self._m1_diagnostics(direct, "AIDL-R004")
        self.assertEqual(1, len(direct_cycle))
        self.assertEqual((1, 1), (direct_cycle[0].location.line, direct_cycle[0].location.column))
        self.assertEqual(
            "cyclic module dependency: cycle.self -> cycle.self",
            direct_cycle[0].message,
        )

        sources = {
            "a.aidl": """module cycle.a
import cycle.b.B
export value A {
  id: uuid required
}
""",
            "b.aidl": """module cycle.b
import cycle.c.C
export value B {
  id: uuid required
}
""",
            "c.aidl": """module cycle.c
import cycle.a.A
export value C {
  id: uuid required
}
""",
        }
        paths = self._paths(sources)
        first = load_compiler_analysis(paths)
        second = load_compiler_analysis(paths)
        first_cycles = [item.to_json() for item in self._m1_diagnostics(first, "AIDL-R004")]
        second_cycles = [item.to_json() for item in self._m1_diagnostics(second, "AIDL-R004")]
        self.assertEqual(first_cycles, second_cycles)
        self.assertEqual(1, len(first_cycles))
        self.assertEqual(
            "cyclic module dependency: cycle.a -> cycle.b -> cycle.c -> cycle.a",
            first_cycles[0]["message"],
        )
        self.assertEqual(1, first_cycles[0]["location"]["line"])
        self.assertEqual(1, first_cycles[0]["location"]["column"])


if __name__ == "__main__":
    unittest.main()
