from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.core_bootstrap import (
    BootstrapSyntaxError,
    KERNEL_META_COMBINATORS,
    KERNEL_VERSION,
    parse_bootstrap_source,
    parse_expression,
    parse_meta_combinator,
    parse_source,
    parse_type_ref,
)

ROOT = Path(__file__).resolve().parents[1]


class CoreBootstrapTest(unittest.TestCase):
    def test_universal_declaration_envelope_and_argument_contracts(self) -> None:
        program = parse_source(
            "module sample\n"
            "entity Zero {}\n"
            "query Fixed(id: Id) -> User? {}\n"
            "declaration Open(args?: ...) -> any {}\n"
        )
        zero, fixed, opened = program.declarations
        self.assertFalse(zero.arguments_present)
        self.assertEqual(fixed.argument_specs[0].type_ref.name, "Id")
        self.assertEqual(opened.open_arguments_binder, "args")
        with self.assertRaisesRegex(BootstrapSyntaxError, "empty declaration argument list"):
            parse_source("module sample\nentity Invalid() {}\n")

    def test_nullable_generic_typerefs_and_named_declarations_are_domain_free(self) -> None:
        type_ref = parse_type_ref("Page<User?>?")
        self.assertEqual(type_ref.name, "Page")
        self.assertTrue(type_ref.optional)
        self.assertTrue(type_ref.arguments[0].optional)
        program = parse_bootstrap_source(
            "module sample\n"
            "enum Requirement { case REQUIRED }\n"
            "query find(id: Id) -> Page<Requirement> {}\n"
        )
        self.assertEqual([item.name for item in program.declarations], ["Requirement", "find"])

    def test_body_continuation_and_modifiers_ignore_indentation(self) -> None:
        source = (
            "module sample\n"
            "entity User {\n"
            "field id:\n"
            "UserId\n"
            "@primary\n"
            "invariant:\n"
            "amount > 0\n"
            "}\n"
        )
        entity = parse_source(source).declarations[0]
        self.assertEqual(entity.body[0].name, "id")
        self.assertEqual(entity.body[0].modifiers[0].name, "primary")
        self.assertEqual(entity.body[1].value.raw, "amount > 0")

    def test_expression_precedence_ranges_lists_references_and_postfix(self) -> None:
        for expression in (
            "1 + 2 * 3 >= 7 && true || false",
            "0..*",
            "[1, 2, user.id]",
            "service.find(id: user.id)[0].name",
            "!(amount <= 0)",
        ):
            self.assertIsNotNone(parse_expression(expression))
        with self.assertRaises(BootstrapSyntaxError):
            parse_expression("0..")

    def test_strings_interpolation_multiline_language_tags_and_nested_comments(self) -> None:
        for expression in (
            '"Hello $name ${price * amount} $$"',
            '"""\nHello $user.name\n"""',
            '"""SQL\nSELECT * FROM users WHERE id = ${id}\n"""',
        ):
            self.assertEqual(parse_expression(expression).kind, "string")
        parsed = parse_source("module sample\n/* outer /* nested */ ok */\nentity User {}\n")
        self.assertEqual(parsed.declarations[0].name, "User")
        with self.assertRaises(BootstrapSyntaxError):
            parse_expression('"bad $"')

    def test_statement_end_semicolon_and_newline(self) -> None:
        program = parse_source("module sample; import other.mod as other; entity A {}; entity B {}\n")
        self.assertEqual(program.module, "sample")
        self.assertEqual(program.import_aliases, (("other.mod", "other"),))
        self.assertEqual([item.name for item in program.declarations], ["A", "B"])

    def test_finite_structural_meta_combinators_parse_and_obsolete_markers_fail(self) -> None:
        samples = {
            "name(required)": "name",
            "args(type, cardinal(optional))": "args",
            "body(type, name(required), cardinal(many))": "body",
            "cardinal(optional)": "cardinal",
            "modifier(primary, cardinal(optional))": "modifier",
        }
        self.assertEqual(tuple(samples.values()), KERNEL_META_COMBINATORS)
        for source, expected in samples.items():
            self.assertEqual(parse_meta_combinator(source).name, expected)
        for obsolete in ("produces(type)", "type-position"):
            with self.assertRaises(BootstrapSyntaxError):
                parse_meta_combinator(obsolete)

    def test_duplicate_bindings_fail_closed(self) -> None:
        duplicate = "module sample\nfirst Same {}\nsecond Same {}\n"
        self.assertEqual(len(parse_source(duplicate).declarations), 2)
        with self.assertRaisesRegex(BootstrapSyntaxError, "duplicate or ambiguous bootstrap binding"):
            parse_bootstrap_source(duplicate)

    def test_kernel_contract_records_normative_ebnf_boundary(self) -> None:
        contract = json.loads((ROOT / "spec" / "bootstrap-kernel-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["kernelVersion"], KERNEL_VERSION)
        self.assertTrue(contract["bindingCoreEbnf"]["emptyDeclarationParenthesesRejected"])
        self.assertTrue(contract["bindingCoreEbnf"]["newlineTerminationOnlyWhenComplete"])
        self.assertTrue(contract["bindingCoreEbnf"]["nestedBlockComments"])
        self.assertTrue(contract["bindingCoreEbnf"]["rawMultilineStrings"])
        self.assertTrue(contract["authorityFirewall"]["directAidlDeclarationKindContractsAreNormative"])
        self.assertFalse(contract["authorityFirewall"]["producerCapabilitySystemOwnedByHost"])
        self.assertEqual(contract["typeRef"]["carrierIdentity"], "generic-visible-named-declaration-symbol")


if __name__ == "__main__":
    unittest.main()
