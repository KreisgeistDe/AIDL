from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates
from tools.compiler_typecheck import _serial, parse_type


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"


def _document(source_id: str, source: str):
    program, diagnostics, _tokens = parse_text(source)
    if diagnostics:
        raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
    return compiler_document_from_ast(Path(f"{source_id}.source"), program)


def _project():
    consumer = _document(
        "consumer",
        "module demo.consumer\n"
        "import demo.shared.*\n"
        "entity Holder {}\n",
    )
    provider_a = _document(
        "provider-a",
        "module demo.shared\n"
        "export enum PublicEnum {}\n"
        "export entity PublicEntity {}\n"
        "export value EmptyValue {}\n"
        "export value SecretValue {\n"
        "  field secret: string sensitive\n"
        "}\n"
        "export entity Duplicate {}\n",
    )
    provider_b = _document(
        "provider-b",
        "module demo.shared\n"
        "export enum Duplicate {}\n",
    )
    return compiler_project_from_documents([consumer, provider_a, provider_b])


def oracle_signature() -> str:
    project = _project()
    consumer_item = next(
        item
        for item in project.declaration_names
        if item.fully_qualified_name == "demo.consumer.Holder"
    )
    consumer_document = project.documents[0]
    lines = []
    for type_source in ("string", "[uuid]?", "PublicEnum", "PublicEntity", "EmptyValue", "SecretValue"):
        serializable = _serial(project, consumer_item, parse_type(type_source), set())
        status = "SERIALIZABLE" if serializable else "NOT_SERIALIZABLE"
        diagnostic = "" if serializable else "AIDL-T004"
        lines.append(f"{type_source}|{status}|{diagnostic}")

    duplicate = _reference_candidates(project, consumer_document, "Duplicate")
    missing = _reference_candidates(project, consumer_document, "Missing")
    if len(duplicate) != 2:
        raise AssertionError(f"expected two Duplicate candidates, got {len(duplicate)}")
    if missing:
        raise AssertionError(f"expected Missing to be unresolved, got {len(missing)} candidates")
    lines.append("Duplicate|AMBIGUOUS|CORE-S023")
    lines.append("Missing|UNRESOLVED|AIDL-T001")
    return "\n".join(lines)


class KotlinSerializationChecksParityTest(unittest.TestCase):
    def test_pinned_signature_matches_current_python_and_core_observables(self) -> None:
        expected = (PARITY / "serialization-checks.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_serialization_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
