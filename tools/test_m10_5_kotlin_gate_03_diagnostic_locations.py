from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_core_materialization import collect_core_materialization_issues
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import resolve_project_reference
from tools.compiler_typecheck import collect_type_issues


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"

CONSUMER_SOURCE = (
    "module demo.consumer\n"
    "import demo.shared.*\n"
    "alias RejectedTarget = myQuery\n"
    "alias MissingTarget = Missing\n"
    "alias AmbiguousTarget = Duplicate\n"
    "query WrongDefault(value: string default true) -> string {}\n"
)
PROVIDER_A_SOURCE = (
    "module demo.shared\n"
    "export query myQuery(id: string) -> string {}\n"
    "export entity Duplicate {}\n"
)
PROVIDER_B_SOURCE = (
    "module demo.shared\n"
    "export enum Duplicate { case OTHER }\n"
)


def _document(source_path: str, source: str):
    program, diagnostics, _tokens = parse_text(source)
    if diagnostics:
        raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
    return compiler_document_from_ast(Path(source_path), program)


def _project():
    return compiler_project_from_documents(
        [
            _document("consumer.aidl", CONSUMER_SOURCE),
            _document("provider-a.aidl", PROVIDER_A_SOURCE),
            _document("provider-b.aidl", PROVIDER_B_SOURCE),
        ]
    )


def _offset(marker: str, token: str) -> int:
    marker_offset = CONSUMER_SOURCE.index(marker)
    return marker_offset + len(marker) - len(token)


def _resolution(project, marker: str, token: str):
    document = project.documents[0]
    offset = _offset(marker, token)
    source_texts = {
        document.source_path.absolute().resolve(strict=False): CONSUMER_SOURCE,
    }
    return resolve_project_reference(
        project,
        document.source_path,
        offset,
        source_texts=source_texts,
    )


def _render_issue(label: str, issue) -> str:
    location = issue.location
    return (
        f"{label}|{issue.code}|{issue.source_path}|"
        f"{location.line}:{location.column}:{location.offset}"
    )


def _render_resolution(label: str, code: str, resolution) -> str:
    payload = resolution.to_json()
    if "target" in payload or "location" in payload:
        raise AssertionError(f"resolver diagnostic must not fabricate location: {payload}")
    return f"{label}|{code}||"


def oracle_signature() -> str:
    project = _project()

    materialization_issues = collect_core_materialization_issues(project)
    rejected = [
        issue
        for issue in materialization_issues
        if issue.subject_name == "RejectedTarget" and issue.code == "AIDL-T005"
    ]
    if len(rejected) != 1:
        raise AssertionError(f"expected one real AIDL-T005 RejectedTarget issue, got {rejected}")

    missing = _resolution(project, "= Missing", "Missing")
    ambiguous = _resolution(project, "= Duplicate", "Duplicate")
    if missing.status != "unresolved":
        raise AssertionError(f"expected Missing unresolved, got {missing.status}")
    if ambiguous.status != "ambiguous":
        raise AssertionError(f"expected Duplicate ambiguous, got {ambiguous.status}")

    type_issues = collect_type_issues(project)
    mismatches = [
        issue
        for issue in type_issues
        if issue.subject_name == "WrongDefault" and issue.code == "AIDL-T002"
    ]
    if len(mismatches) != 1:
        raise AssertionError(f"expected one real AIDL-T002 WrongDefault issue, got {mismatches}")

    rejected_issue = rejected[0]
    mismatch_issue = mismatches[0]

    if rejected_issue.location.offset != CONSUMER_SOURCE.index("alias RejectedTarget"):
        raise AssertionError(f"AIDL-T005 is not declaration-anchored: {rejected_issue.location}")
    if mismatch_issue.location.offset != CONSUMER_SOURCE.index("query WrongDefault"):
        raise AssertionError(f"AIDL-T002 is not declaration-anchored: {mismatch_issue.location}")
    if rejected_issue.location.offset == _offset("= myQuery", "myQuery"):
        raise AssertionError("AIDL-T005 must not be certified from TypeRef token arithmetic")
    if mismatch_issue.location.offset == _offset("value: string", "string"):
        raise AssertionError("AIDL-T002 must not be certified from TypeRef token arithmetic")

    return "\n".join(
        (
            _render_issue("materialization-rejected", rejected_issue),
            _render_resolution("resolution-missing", "AIDL-T001", missing),
            _render_resolution("resolution-ambiguous", "CORE-S023", ambiguous),
            _render_issue("type-mismatch", mismatch_issue),
        )
    )


class KotlinGate03DiagnosticLocationParityTest(unittest.TestCase):
    def test_pinned_signature_matches_real_python_frontend_observables(self) -> None:
        expected = (PARITY / "gate-03-diagnostic-locations.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_gate_03_location_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
