from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import aidl_parser  # noqa: E402
import compiler_ast  # noqa: E402


class CompilerAstBoundaryTest(unittest.TestCase):
    def build_document(self, source: str, path: str = "src/example.aidl") -> compiler_ast.CompilerDocument:
        program, diagnostics, _ = aidl_parser.parse_text(source)
        self.assertEqual(diagnostics, [])
        return compiler_ast.compiler_document_from_ast(Path(path), program)

    def test_extracts_module_imports_declarations_path_and_spans(self) -> None:
        document = self.build_document(
            "module example.orders\n"
            "import example.shared.Money\n"
            "import example.shared.*\n"
            "export entity Order {\n"
            "}\n",
            "domain/orders.aidl",
        )

        self.assertEqual(document.source_path, Path("domain/orders.aidl"))
        self.assertEqual(document.module.name, "example.orders")
        self.assertEqual(document.module.span, aidl_parser.Span(1, 1, 0))
        self.assertEqual(document.imports[0].name, "example.shared.Money")
        self.assertFalse(document.imports[0].wildcard)
        self.assertEqual(document.imports[0].span, aidl_parser.Span(2, 1, 22))
        self.assertEqual(document.imports[1].name, "example.shared.*")
        self.assertTrue(document.imports[1].wildcard)
        self.assertEqual(document.imports[1].span.line, 3)
        self.assertEqual([node.kind for node in document.declarations], ["entity"])
        self.assertEqual(document.declarations[0].name, "Order")
        self.assertTrue(document.declarations[0].exported)
        self.assertEqual(document.declarations[0].span.line, 4)
        self.assertIs(document.declarations[0].node, document.top_level[-1])
        self.assertIsNotNone(document.declarations[0].end)
        self.assertEqual(
            [node.kind for node in document.top_level],
            ["module", "import", "import", "entity"],
        )
        self.assertEqual(document.span, aidl_parser.Span(1, 1, 0))
        self.assertIsNotNone(document.end)
        self.assertIsNotNone(document.module.end)
        self.assertTrue(all(item.end is not None for item in document.imports))

    def test_import_order_matches_parser_order(self) -> None:
        document = self.build_document(
            "module example.app\n"
            "import zeta.types.Widget\n"
            "import alpha.types.*\n"
            "import beta.types.Value\n"
        )

        self.assertEqual(
            [item.name for item in document.imports],
            ["zeta.types.Widget", "alpha.types.*", "beta.types.Value"],
        )

    def test_module_and_imports_are_optional_without_losing_declarations(self) -> None:
        document = self.build_document("entity Standalone {\n}\n", "standalone.aidl")

        self.assertIsNone(document.module)
        self.assertEqual(document.imports, ())
        self.assertEqual([node.name for node in document.declarations], ["Standalone"])
        self.assertEqual(
            document.top_level,
            tuple(declaration.node for declaration in document.declarations),
        )

    def test_first_module_is_exposed_without_semantic_validation(self) -> None:
        document = self.build_document(
            "module example.first\n"
            "module example.second\n"
            "entity Value {\n}\n"
        )

        self.assertEqual(document.module.name, "example.first")
        self.assertEqual(
            [node.name for node in document.top_level if node.kind == "module"],
            ["example.first", "example.second"],
        )
        self.assertEqual([node.name for node in document.declarations], ["Value"])

    def test_declaration_headers_preserve_order_kind_export_and_missing_names(self) -> None:
        document = self.build_document(
            "module example.headers\n"
            "export value PublicValue {\n}\n"
            "auth {\n}\n"
            "entity InternalEntity {\n}\n"
        )

        self.assertEqual(
            [(item.kind, item.name, item.exported) for item in document.declarations],
            [
                ("value", "PublicValue", True),
                ("auth", None, False),
                ("entity", "InternalEntity", False),
            ],
        )
        self.assertEqual([item.span.line for item in document.declarations], [2, 4, 6])
        self.assertTrue(all(item.end is not None for item in document.declarations))
        self.assertEqual(
            [item.node for item in document.declarations],
            list(document.top_level[1:]),
        )


if __name__ == "__main__":
    unittest.main()
