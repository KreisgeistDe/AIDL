from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import aidl_parser
from tools.compiler_ast import compiler_document_from_core_program
from tools.core_language import (
    CoreLanguageError,
    check_grammar_projection,
    grammar_projection,
    load_core_authority,
    load_kernel_contract,
    parse_core_language_source,
    validate_core_language_source,
)

ROOT = Path(__file__).resolve().parents[1]


class BreakingCoreP1Test(unittest.TestCase):
    def test_authority_loads_and_revision4_is_not_needed(self) -> None:
        authority = load_core_authority()
        self.assertIn("declaration", authority.core.contracts)
        self.assertEqual("declaration", authority.core.aliases["type"])
        transition = json.loads((ROOT / "spec/core-authority-transition-v1.json").read_text())
        self.assertEqual(
            "spec/core-self-description-v1.aidl",
            transition["activeLanguageAuthority"]["path"],
        )
        historical = {item["path"]: item for item in transition["historicalAuthorities"]}
        self.assertFalse(historical["spec/language-surface-v1.json"]["activeLanguageAuthority"])

    def test_invalid_kernel_and_invalid_core_fail_closed(self) -> None:
        kernel = json.loads((ROOT / "spec/bootstrap-kernel-v1.json").read_text())
        kernel["owns"].append("concrete-declaration-kind-catalog")
        with self.assertRaises(CoreLanguageError):
            load_kernel_contract(json.dumps(kernel))

        source = (ROOT / "spec/core-self-description-v1.aidl").read_text()
        broken = source.replace('semantic alias: "declaration"', 'semantic alias: "missing"')
        with self.assertRaises(CoreLanguageError):
            load_core_authority(core_source=broken)

    def test_active_parser_does_not_use_legacy_declaration_kind_table(self) -> None:
        original = set(aidl_parser.DECLARATION_STARTERS)
        try:
            aidl_parser.DECLARATION_STARTERS.clear()
            program = parse_core_language_source(
                "module demo\nentity Customer {\n  field id: string @primary\n}\n"
            )
            self.assertEqual("entity", program.declarations[0].kind)
        finally:
            aidl_parser.DECLARATION_STARTERS.clear()
            aidl_parser.DECLARATION_STARTERS.update(original)

    def test_generic_envelope_structurally_covers_p1_surface(self) -> None:
        program = parse_core_language_source(
            "module demo\n"
            "entity Customer<T> {\n"
            "  field owner: ref<CoreEntityExample> @primary(source: \"core\")\n"
            "  invariant ready: expression<bool>\n"
            "}\n"
            "query find(id: Id) -> Page<Customer> {}\n"
        )
        entity, query = program.declarations
        self.assertEqual("T", entity.generic_parameters[0].name)
        self.assertEqual("ref", entity.body[0].value.value.name)
        self.assertEqual("CoreEntityExample", entity.body[0].value.value.arguments[0].name)
        self.assertEqual("source", entity.body[0].modifiers[0].arguments[0][0])
        self.assertEqual("expression", entity.body[1].value.value.name)
        self.assertEqual("bool", entity.body[1].value.value.arguments[0].name)
        self.assertEqual("Id", query.argument_specs[0].type_ref.name)
        self.assertEqual("Page", query.result.name)
        document = compiler_document_from_core_program(Path("demo.aidl"), program)
        self.assertEqual(["entity", "query"], [item.kind for item in document.declarations])

    def test_minimal_semantic_source_is_core_driven(self) -> None:
        diagnostics = validate_core_language_source(
            "module demo\nentity Customer {\n  field id: string @primary\n}\n"
        )
        self.assertEqual((), diagnostics)

    def test_grammar_projection_cannot_drift(self) -> None:
        check_grammar_projection()
        text = (ROOT / "docs/06-grammar.md").read_text()
        self.assertIn(grammar_projection(), text)


if __name__ == "__main__":
    unittest.main()
