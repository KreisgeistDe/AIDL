from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates
from tools.compiler_typecheck import TypeSyntaxError, parse_type


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
SOURCE_IDS = ["resolution-consumer", "resolution-provider-a", "resolution-provider-b"]
CASES = [
    ("string", "string"),
    ("[uuid]?", "[uuid]?"),
    ("Public?", "Public?"),
    ("demo.shared.Public", "demo.shared.Public"),
    ("Local", "Local"),
    ("Duplicate", "Duplicate"),
    ("Missing", "Missing"),
    ("<blank>", ""),
    ("string??", "string??"),
    ("[string", "[string"),
    ("string]", "string]"),
]


def _project():
    documents = []
    for source_id in SOURCE_IDS:
        source_path = PARITY / f"{source_id}.source"
        program, diagnostics, _tokens = parse_text(source_path.read_text(encoding="utf-8"))
        if diagnostics:
            raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
        documents.append(compiler_document_from_ast(Path(f"{source_id}.source"), program))
    return compiler_project_from_documents(documents)


def _identity(candidate) -> str:
    document = candidate.document
    index = document.declarations.index(candidate.declaration)
    return f"{candidate.fully_qualified_name}@{document.source_path.stem}#{index}"


def _shape(type_ref) -> str:
    if type_ref.kind == "nullable":
        return f"nullable({_shape(type_ref.args[0])})"
    if type_ref.kind == "list":
        return f"list({_shape(type_ref.args[0])})"
    if type_ref.kind in {"scalar", "named"}:
        return f"{type_ref.kind}:{type_ref.name}"
    return type_ref.kind


def _nominal_name(type_ref) -> str | None:
    while type_ref.kind in {"nullable", "list"} and type_ref.args:
        type_ref = type_ref.args[0]
    return type_ref.name if type_ref.kind == "named" else None


def oracle_signature() -> str:
    project = _project()
    consumer = project.documents[0]
    lines = []
    for label, source in CASES:
        try:
            type_ref = parse_type(source)
        except TypeSyntaxError:
            lines.append(f"{label}|REJECT|||")
            continue
        status = "RESOLVED"
        symbols = []
        name = _nominal_name(type_ref)
        if name is not None:
            candidates = _reference_candidates(project, consumer, name)
            status = "UNRESOLVED" if not candidates else "RESOLVED" if len(candidates) == 1 else "AMBIGUOUS"
            symbols = [_identity(candidate) for candidate in candidates]
        lines.append(f"{label}|ACCEPT|{_shape(type_ref)}|{status}|{','.join(symbols)}")
    return "\n".join(lines)


class KotlinTypeConstructionParityTest(unittest.TestCase):
    def test_pinned_signature_matches_current_python_core_oracle(self) -> None:
        expected = (PARITY / "type-construction.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_type_construction_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
