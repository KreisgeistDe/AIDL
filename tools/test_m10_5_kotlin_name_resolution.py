from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
SOURCE_IDS = ["resolution-consumer", "resolution-provider-a", "resolution-provider-b"]
QUERIES = ["Local", "Public", "Hidden", "demo.shared.Hidden", "Duplicate", "Missing"]


def _identity(candidate) -> str:
    document = candidate.document
    index = document.declarations.index(candidate.declaration)
    source_id = document.source_path.stem
    return f"{candidate.fully_qualified_name}@{source_id}#{index}"


def oracle_signature() -> str:
    documents = []
    for source_id in SOURCE_IDS:
        source_path = PARITY / f"{source_id}.source"
        program, diagnostics, _tokens = parse_text(source_path.read_text(encoding="utf-8"))
        if diagnostics:
            raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
        documents.append(compiler_document_from_ast(Path(f"{source_id}.source"), program))

    project = compiler_project_from_documents(documents)
    consumer = project.documents[0]
    symbols = ",".join(
        _identity(candidate)
        for candidate in project.declaration_names
        if candidate.fully_qualified_name is not None
    )
    imports = ";".join(
        f"{resolution.document.source_path.stem}|{resolution.import_.name}|"
        + ",".join(_identity(candidate) for candidate in resolution.declarations)
        for resolution in project.import_resolutions
    )
    queries = []
    for reference in QUERIES:
        candidates = _reference_candidates(project, consumer, reference)
        status = "UNRESOLVED" if not candidates else "RESOLVED" if len(candidates) == 1 else "AMBIGUOUS"
        queries.append(f"{reference}|{status}|" + ",".join(_identity(candidate) for candidate in candidates))
    return f"symbols={symbols}\nimports={imports}\nqueries={';'.join(queries)}"


class KotlinNameResolutionParityTest(unittest.TestCase):
    def test_shared_resolution_fixture_is_pinned_to_python_oracle(self) -> None:
        expected = (PARITY / "resolution.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_resolution_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
