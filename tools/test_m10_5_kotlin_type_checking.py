from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates
from tools.compiler_typecheck import collect_type_issues


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
RESOLUTION_SOURCES = ["resolution-consumer", "resolution-provider-a", "resolution-provider-b"]
DEFAULT_CASES = [
    ("string", '"ok"'),
    ("bool", "true"),
    ("int", "-1"),
    ("decimal", "1"),
    ("decimal", "1.5"),
    ("string?", "null"),
    ("string", "null"),
    ("int", "true"),
]


def _document(source_id: str, source: str):
    program, diagnostics, _tokens = parse_text(source)
    if diagnostics:
        raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
    return compiler_document_from_ast(Path(f"{source_id}.source"), program)


def _default_status(type_source: str, literal_source: str) -> tuple[str, str]:
    source = (
        "module demo.consumer\n"
        f"query Q(value: {type_source} default {literal_source}) -> string {{}}\n"
    )
    project = compiler_project_from_documents([_document("default-case", source)])
    issues = collect_type_issues(project)
    matching = [issue for issue in issues if issue.code == "AIDL-T002"]
    if matching:
        return "TYPE_MISMATCH", "AIDL-T002"
    return "ASSIGNABLE", ""


def _resolution_project():
    documents = []
    for source_id in RESOLUTION_SOURCES:
        source = (PARITY / f"{source_id}.source").read_text(encoding="utf-8")
        documents.append(_document(source_id, source))
    return compiler_project_from_documents(documents)


def oracle_signature() -> str:
    lines = []
    for type_source, literal_source in DEFAULT_CASES:
        status, diagnostic = _default_status(type_source, literal_source)
        lines.append(f"{type_source}|{literal_source}|{status}|{diagnostic}")

    project = _resolution_project()
    consumer = project.documents[0]
    duplicate = _reference_candidates(project, consumer, "Duplicate")
    missing = _reference_candidates(project, consumer, "Missing")
    if len(duplicate) != 2:
        raise AssertionError(f"expected two Duplicate candidates, got {len(duplicate)}")
    if missing:
        raise AssertionError(f"expected Missing to be unresolved, got {len(missing)} candidates")
    lines.append('Duplicate|"x"|AMBIGUOUS|CORE-S023')
    lines.append('Missing|"x"|UNRESOLVED|AIDL-T001')
    return "\n".join(lines)


class KotlinTypeCheckingParityTest(unittest.TestCase):
    def test_pinned_signature_matches_current_python_and_core_observables(self) -> None:
        expected = (PARITY / "type-checking.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_type_checking_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
