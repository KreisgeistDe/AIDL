from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
CASES = [
    ("positive", "source-projection-positive.source", True),
    ("unexpected-character", "source-projection-unexpected-character.source", False),
    ("unterminated-comment", "source-projection-unterminated-comment.source", False),
    ("newline-string", "source-projection-newline-string.source", False),
]


def _case_signature(case_name: str, filename: str, expected_accepted: bool) -> str:
    source_path = PARITY / filename
    source = source_path.read_text(encoding="utf-8")
    program, diagnostics, _tokens = parse_text(source)
    relative_path = Path("parity") / filename
    document = compiler_document_from_ast(relative_path, program)
    source_id = source_path.stem
    if document.source_path.stem != source_id:
        raise AssertionError((document.source_path, source_id))

    prefix = f"{case_name}|sourceId={source_id}|path={document.source_path.as_posix()}"
    if diagnostics:
        if expected_accepted:
            raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
        diagnostic = diagnostics[0]
        return (
            f"{prefix}|accepted=false|diagnostic={diagnostic.message}"
            f"@{diagnostic.start.offset}"
        )

    if not expected_accepted:
        raise AssertionError(f"{filename} unexpectedly parsed without diagnostics")

    project = compiler_project_from_documents([document])
    projected = project.documents[0]
    for declaration in projected.declarations:
        candidates = _reference_candidates(project, projected, declaration.name or "")
        if len(candidates) != 1 or candidates[0].declaration is not declaration:
            raise AssertionError((declaration.name, candidates))

    module = projected.module.name if projected.module is not None else ""
    imports = ",".join(import_.name or "" for import_ in projected.imports)
    declarations = ",".join(
        f"{declaration.kind}:{declaration.name}:{str(declaration.exported).lower()}"
        f"@{declaration.span.offset if declaration.span is not None else -1}"
        for declaration in projected.declarations
    )
    return (
        f"{prefix}|accepted=true|module={module}|imports={imports}"
        f"|declarations={declarations}"
    )


def oracle_signature() -> str:
    return "\n".join(_case_signature(*case) for case in CASES)


class KotlinSourceProjectionParityTest(unittest.TestCase):
    def test_shared_source_projection_fixtures_are_pinned_to_python_oracle(self) -> None:
        expected = (PARITY / "source-projection.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_source_projection_python_oracle_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
