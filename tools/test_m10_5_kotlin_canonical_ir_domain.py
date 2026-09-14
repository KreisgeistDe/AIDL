from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_diagnostics import CompilerAnalysis, collect_compiler_diagnostics
from tools.compiler_ir import build_canonical_ir
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates
from tools.ir_identity import IrIdentityError, declaration_identity


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
DOMAIN_REL = Path("compiler/kotlin/parity/canonical-ir-domain.source")
ENVELOPE_REL = Path("compiler/kotlin/parity/canonical-ir-envelope.source")
MISSING_MODULE_REL = Path("compiler/kotlin/parity/canonical-ir-domain-missing-module.source")
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))
DOMAIN_MODULE = "parity.ir.domain"


def _type_signature(type_ref: dict) -> str:
    kind = type_ref["kind"]
    if kind == "scalar":
        return f"scalar:{type_ref['name']}"
    if kind == "named":
        suffix = ""
        arguments = type_ref["typeArguments"]
        if arguments:
            suffix = "<" + ",".join(_type_signature(argument) for argument in arguments) + ">"
        return f"named:{type_ref['declarationId']}:{type_ref['fqn']}{suffix}"
    if kind in {"list", "set", "nullable"}:
        return f"{kind}<{_type_signature(type_ref['element'])}>"
    if kind == "map":
        return f"map<{_type_signature(type_ref['key'])},{_type_signature(type_ref['value'])}>"
    if kind == "ref":
        return f"ref:{type_ref['entityId']}:{type_ref['entityFqn']}:{type_ref['ownerServiceId']}"
    if kind == "record":
        fields = ",".join(
            f"{field['name']}={_type_signature(field['type'])}|required={str(field['required']).lower()}"
            for field in type_ref["fields"]
        )
        return f"record<{fields}>"
    raise AssertionError(f"unexpected type kind {kind!r}")


def _field_signature(field: dict) -> str:
    return (
        f"{field['name']}={_type_signature(field['type'])}"
        f"|required={str(field['required']).lower()}"
        f"|mutable={str(field['mutable']).lower()}"
        f"|sensitive={str(field['sensitive']).lower()}"
        f"|generated={str(field['generated']).lower()}"
        f"|primary={str(field['primary']).lower()}"
        f"|concurrencyToken={str(field['concurrencyToken']).lower()}"
        f"|onDelete={field['onDelete']}"
    )


def _declaration_signature(index: int, declaration: dict) -> str:
    prefix = (
        f"declaration|{index}|{declaration['kind']}|{declaration['declarationId']}"
        f"|{declaration['fqn']}|{declaration['name']}|{declaration['ownerModule']}"
    )
    if declaration["kind"] == "enum":
        return f"{prefix}|values={','.join(declaration['values'])}"
    fields = ";".join(_field_signature(field) for field in declaration["fields"])
    if declaration["kind"] == "entity":
        return f"{prefix}|fields={fields}|identityFields={','.join(declaration['identityFields'])}"
    return f"{prefix}|fields={fields}"


def _source_entry_signature(entry: dict) -> str:
    span = entry["span"]
    return (
        f"sourceMap|{entry['nodePath']}|{entry['originalDeclarationId']}|{span['file']}"
        f":{span['startLine']}:{span['startColumn']}-{span['endLine']}:{span['endColumn']}"
    )


def _assert_schema_valid(document: dict) -> None:
    validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        raise AssertionError("\n".join(error.message for error in errors))


def _analysis_from_shared_sources() -> CompilerAnalysis:
    documents = []
    parser_diagnostics = {}
    for source_path in (DOMAIN_REL, ENVELOPE_REL):
        source = (ROOT / source_path).read_text(encoding="utf-8")
        program, diagnostics, _tokens = parse_text(source)
        documents.append(compiler_document_from_ast(source_path, program))
        parser_diagnostics[source_path] = diagnostics
    project = compiler_project_from_documents(documents)
    return CompilerAnalysis(
        project=project,
        diagnostics=collect_compiler_diagnostics(project, parser_diagnostics),
    )


def _positive_document() -> dict:
    analysis = _analysis_from_shared_sources()
    errors = [
        diagnostic.to_json()
        for diagnostic in analysis.diagnostics
        if diagnostic.severity.value == "error"
    ]
    if errors:
        raise AssertionError(errors)

    domain_document = next(
        document
        for document in analysis.project.documents
        if document.module is not None and document.module.name == DOMAIN_MODULE
    )
    for declaration in domain_document.declarations:
        candidates = _reference_candidates(
            analysis.project,
            domain_document,
            declaration.name or "",
        )
        if len(candidates) != 1 or candidates[0].declaration is not declaration:
            raise AssertionError((declaration.name, candidates))

    document = build_canonical_ir(analysis)
    _assert_schema_valid(document)
    return document


def _missing_module_rejected() -> bool:
    source = (ROOT / MISSING_MODULE_REL).read_text(encoding="utf-8")
    program, diagnostics, _tokens = parse_text(source)
    if diagnostics:
        raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
    document = compiler_document_from_ast(MISSING_MODULE_REL, program)
    project = compiler_project_from_documents([document])
    item = project.declaration_names[0]
    try:
        declaration_identity(item, 1)
    except IrIdentityError:
        return True
    raise AssertionError("missing-module declaration unexpectedly gained canonical IR identity")


def oracle_signature() -> str:
    document = _positive_document()
    domain_declarations = [
        declaration
        for declaration in document["declarations"]
        if declaration["ownerModule"] == DOMAIN_MODULE
    ]
    domain_ids = {declaration["declarationId"] for declaration in domain_declarations}
    source_entries = [
        entry
        for entry in document["sourceMap"]["entries"]
        if entry["originalDeclarationId"] in domain_ids
    ]
    lines = ["schema=valid"]
    lines.extend(
        _declaration_signature(index, declaration)
        for index, declaration in enumerate(domain_declarations)
    )
    lines.extend(_source_entry_signature(entry) for entry in source_entries)
    lines.append(f"negative|missing-module|rejected={str(_missing_module_rejected()).lower()}")
    return "\n".join(lines)


class KotlinCanonicalIrDomainParityTest(unittest.TestCase):
    def test_real_python_full_ir_pins_bounded_kotlin_domain_slice(self) -> None:
        expected = (PARITY / "canonical-ir-domain.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_reference_full_document_is_schema_valid_and_deterministic(self) -> None:
        first = _positive_document()
        second = _positive_document()
        self.assertEqual(first, second)
        _assert_schema_valid(first)
        self.assertEqual("0.3.0", first["irVersion"])
        self.assertTrue(first["semanticHash"].startswith("sha256:"))
        self.assertTrue(
            all(item["semanticHash"].startswith("sha256:") for item in first["declarations"])
        )

    def test_missing_module_boundary_fails_closed_before_ir_identity(self) -> None:
        self.assertTrue(_missing_module_rejected())


if __name__ == "__main__":
    unittest.main()
