from pathlib import Path
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_core_materialization import collect_core_materialization_issues
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates
from tools.compiler_typecheck import parse_type


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
CORE = ROOT / "spec" / "core-self-description-v1.aidl"


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
        "alias StringTarget = string\n"
        "alias EntityTarget = PublicEntity\n"
        "alias ListTarget = [PublicEntity]?\n"
        "alias ProjectGenericTarget = PublicEntity<PublicEnum>\n"
        "alias StandardGenericTarget = Page<PublicEntity>\n"
        "alias BindingCoreGenericTarget = Page<myQuery>\n"
        "entity Holder {}\n",
    )
    provider_a = _document(
        "provider-a",
        "module demo.shared\n"
        "export enum PublicEnum { case PUBLIC }\n"
        "export entity PublicEntity {}\n"
        "export entity Duplicate {}\n",
    )
    provider_b = _document(
        "provider-b",
        "module demo.shared\n"
        "export enum Duplicate { case OTHER }\n",
    )
    return compiler_project_from_documents([consumer, provider_a, provider_b])


def oracle_signature() -> str:
    project = _project()
    consumer_document = project.documents[0]
    issues = {
        issue.subject_name: issue
        for issue in collect_core_materialization_issues(project)
    }
    expected_project_generic = issues.get("ProjectGenericTarget")
    if expected_project_generic is None or expected_project_generic.code != "AIDL-T005":
        raise AssertionError("project generic target must be rejected by AIDL-T005 materialization boundary")
    unexpected = set(issues) - {"ProjectGenericTarget"}
    if unexpected:
        raise AssertionError(f"unexpected materialization issues: {sorted(unexpected)}")

    duplicate = _reference_candidates(project, consumer_document, "Duplicate")
    missing = _reference_candidates(project, consumer_document, "Missing")
    if len(duplicate) != 2:
        raise AssertionError(f"expected two Duplicate candidates, got {len(duplicate)}")
    if missing:
        raise AssertionError(f"expected Missing to be unresolved, got {len(missing)} candidates")

    core_source = CORE.read_text(encoding="utf-8")
    if "query myQuery(id: Id) -> Page<myQuery> {}" not in core_source:
        raise AssertionError("binding Core generic query evidence drifted")
    parse_type("Page<myQuery>")

    return "\n".join(
        (
            "string|MATERIALIZABLE|",
            "PublicEntity|MATERIALIZABLE|",
            "[PublicEntity]?|MATERIALIZABLE|",
            "PublicEntity<PublicEnum>|REJECTED|AIDL-T005",
            "Page<PublicEntity>|MATERIALIZABLE|",
            "Page<myQuery>|OUTSIDE_SLICE|",
            "Duplicate|AMBIGUOUS|CORE-S023",
            "Missing|UNRESOLVED|AIDL-T001",
        )
    )


class KotlinMaterializationBoundaryParityTest(unittest.TestCase):
    def test_pinned_signature_matches_python_and_direct_core_observables(self) -> None:
        expected = (PARITY / "materialization-boundary.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_materialization_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
