from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_core_materialization import collect_core_materialization_issues
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import resolve_project_reference
from tools.compiler_typecheck import parse_type


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
CORE = ROOT / "spec" / "core-self-description-v1.aidl"

CONSUMER_SOURCE = (
    "module demo.consumer\n"
    "import demo.shared.*\n"
    "query myQuery(id: string) -> string {}\n"
    "alias QueryTarget = myQuery\n"
    "alias MissingTarget = Missing\n"
    "alias AmbiguousTarget = Duplicate\n"
    "alias BindingCoreGenericTarget = Page<myQuery>\n"
    "alias AcceptedTarget = PublicEntity\n"
)
PROVIDER_A_SOURCE = (
    "module demo.shared\n"
    "export enum PublicEnum { case PUBLIC }\n"
    "export entity PublicEntity {}\n"
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


def _resolution(project, reference: str):
    document = project.documents[0]
    marker = f"= {reference}"
    offset = CONSUMER_SOURCE.index(marker) + 2
    source_texts = {
        document.source_path.absolute().resolve(strict=False): CONSUMER_SOURCE,
    }
    return resolve_project_reference(
        project,
        document.source_path,
        offset,
        source_texts=source_texts,
    )


def oracle_signature() -> str:
    project = _project()
    issues = collect_core_materialization_issues(project)

    query_issue = next(
        (
            issue
            for issue in issues
            if issue.subject_name == "QueryTarget" and issue.code == "AIDL-T005"
        ),
        None,
    )
    if query_issue is None:
        raise AssertionError("expected QueryTarget to expose AIDL-T005 materialization location")
    if str(query_issue.source_path) != "consumer.aidl":
        raise AssertionError(f"unexpected QueryTarget source path: {query_issue.source_path}")
    query_location = query_issue.location
    if (query_location.line, query_location.column, query_location.offset) != (4, 1, 81):
        raise AssertionError(f"unexpected QueryTarget location: {query_location}")

    missing = _resolution(project, "Missing")
    ambiguous = _resolution(project, "Duplicate")
    if missing.status != "unresolved":
        raise AssertionError(f"expected Missing to remain unresolved, got {missing.status}")
    if ambiguous.status != "ambiguous":
        raise AssertionError(f"expected Duplicate to remain ambiguous, got {ambiguous.status}")
    for label, resolution in (("Missing", missing), ("Duplicate", ambiguous)):
        payload = resolution.to_json()
        if "target" in payload or "location" in payload:
            raise AssertionError(f"{label} resolver contract must not invent a target location: {payload}")

    accepted_issues = [issue for issue in issues if issue.subject_name == "AcceptedTarget"]
    if accepted_issues:
        raise AssertionError(f"accepted PublicEntity target unexpectedly materialization-blocked: {accepted_issues}")

    core_source = CORE.read_text(encoding="utf-8")
    if "query myQuery(id: Id) -> Page<myQuery> {}" not in core_source:
        raise AssertionError("binding Core generic query evidence drifted")
    parse_type("Page<myQuery>")

    return "\n".join(
        (
            "query|REJECTED|AIDL-T005|consumer.aidl|4|1|81",
            "missing|UNRESOLVED|AIDL-T001||||",
            "ambiguous|AMBIGUOUS|CORE-S023||||",
            "binding-core-generic|OUTSIDE_SLICE|||||",
            "accepted|MATERIALIZABLE|||||",
        )
    )


class KotlinMaterializationLocationParityTest(unittest.TestCase):
    def test_pinned_location_signature_matches_python_and_direct_core_observables(self) -> None:
        expected = (PARITY / "materialization-locations.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_materialization_location_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
