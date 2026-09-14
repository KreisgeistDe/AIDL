from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_diagnostics import CoreTypeDiagnosticCode, CompilerDiagnosticSeverity
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates
from tools.compiler_typecheck import TypeSyntaxError, _check_type, parse_type


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
NEGATIVE_CASES = [
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


def _nominal_name(type_ref) -> str | None:
    while type_ref.kind in {"nullable", "list"} and type_ref.args:
        type_ref = type_ref.args[0]
    return type_ref.name if type_ref.kind == "named" else None


def _consumer_local(project):
    consumer = project.documents[0]
    return next(
        item
        for item in project.declaration_names
        if item.document is consumer
        and item.declaration.kind == "entity"
        and item.declaration.name == "Local"
    )


def oracle_signature() -> str:
    project = _project()
    consumer = project.documents[0]
    lines = []
    for label, source in CASES:
        try:
            type_ref = parse_type(source)
        except TypeSyntaxError:
            lines.append(f"{label}|REJECT||")
            continue
        status = "RESOLVED"
        symbols = []
        name = _nominal_name(type_ref)
        if name is not None:
            candidates = _reference_candidates(project, consumer, name)
            status = "UNRESOLVED" if not candidates else "RESOLVED" if len(candidates) == 1 else "AMBIGUOUS"
            symbols = [_identity(candidate) for candidate in candidates]
        lines.append(f"{label}|ACCEPT|{status}|{','.join(symbols)}")
    return "\n".join(lines)


def diagnostic_oracle_signature() -> str:
    project = _project()
    subject = _consumer_local(project)
    rows = []
    expected_messages = {
        "<blank>": "empty type expression",
        "string??": "nullable requires one non-nullable operand",
        "[string": "list requires one element type",
        "string]": "invalid Core type expression 'string]'",
    }
    for label, source in NEGATIVE_CASES:
        issues = _check_type(project, subject, source)
        if len(issues) != 1:
            raise AssertionError(f"{label} expected one TypeIssue, got {issues}")
        issue = issues[0]
        if issue.code != "AIDL-T001":
            raise AssertionError(f"{label} unexpected code: {issue.code}")
        if issue.message != expected_messages[label]:
            raise AssertionError(f"{label} unexpected message: {issue.message}")
        if issue.subject_kind != "entity" or issue.subject_name != "Local":
            raise AssertionError(
                f"{label} unexpected subject: {issue.subject_kind} {issue.subject_name}"
            )
        if str(issue.source_path) != "resolution-consumer.source":
            raise AssertionError(f"{label} unexpected source path: {issue.source_path}")
        location = issue.location
        if (location.line, location.column, location.offset) != (4, 1, 68):
            raise AssertionError(f"{label} unexpected location: {location}")
        if issue.expected != "well-formed Core type constructor":
            raise AssertionError(f"{label} unexpected expected payload: {issue.expected}")
        rows.append(
            (
                issue.source_path.as_posix(),
                location.offset,
                "type",
                CompilerDiagnosticSeverity.ERROR.value,
                CoreTypeDiagnosticCode(issue.code).value,
                issue.message,
                issue,
            )
        )

    rows.sort(key=lambda row: row[:6])
    rendered = []
    for _path, _offset, phase, severity, code, _message, issue in rows:
        rendered.append(
            "|".join(
                (
                    code,
                    phase,
                    severity,
                    issue.message,
                    issue.subject_kind,
                    issue.subject_name,
                    issue.source_path.as_posix(),
                    str(issue.location.line),
                    str(issue.location.column),
                    str(issue.location.offset),
                    issue.expected,
                    f"aidl://diagnostics/{issue.code}",
                )
            )
        )
    return "\n".join(rendered)


class KotlinTypeConstructionParityTest(unittest.TestCase):
    def test_pinned_signature_matches_current_python_core_oracle(self) -> None:
        expected = (PARITY / "type-construction.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_type_construction_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())

    def test_pinned_negative_diagnostic_signature_matches_python_typecheck(self) -> None:
        expected = (PARITY / "type-construction-diagnostics.signature").read_text(
            encoding="utf-8"
        ).rstrip("\n")
        self.assertEqual(expected, diagnostic_oracle_signature())

    def test_negative_diagnostic_signature_is_deterministic(self) -> None:
        self.assertEqual(diagnostic_oracle_signature(), diagnostic_oracle_signature())


if __name__ == "__main__":
    unittest.main()
