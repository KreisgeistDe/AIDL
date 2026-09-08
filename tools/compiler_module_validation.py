"""Stable Module document-structure and dependency-cycle validation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from .aidl_parser import Span
    from .compiler_project import CompilerProject
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from aidl_parser import Span
    from compiler_project import CompilerProject


@dataclass(frozen=True)
class ModuleValidationIssue:
    code: str
    message: str
    source_path: Path
    location: Span
    subject_name: str
    expected: str


def _structure_issues(project: CompilerProject) -> list[ModuleValidationIssue]:
    issues: list[ModuleValidationIssue] = []
    for document in project.documents:
        modules = []
        saw_non_module = False
        for node in document.top_level:
            if node.kind != "module":
                saw_non_module = True
                continue
            if node.span is None:
                continue
            module_name = node.name or "<unnamed>"
            if modules:
                first_name = modules[0].name or "<unnamed>"
                issues.append(
                    ModuleValidationIssue(
                        code="AIDL-R003",
                        message=(
                            f"document declares module '{module_name}' more than once; "
                            f"first module is '{first_name}'"
                        ),
                        source_path=document.source_path,
                        location=node.span,
                        subject_name=module_name,
                        expected="at most one module declaration per file",
                    )
                )
            if saw_non_module:
                issues.append(
                    ModuleValidationIssue(
                        code="AIDL-R003",
                        message=(
                            f"module '{module_name}' must appear before imports and declarations"
                        ),
                        source_path=document.source_path,
                        location=node.span,
                        subject_name=module_name,
                        expected="leading module declaration before imports and declarations",
                    )
                )
            modules.append(node)
    return issues


def _cycle_issues(project: CompilerProject) -> list[ModuleValidationIssue]:
    issues: list[ModuleValidationIssue] = []
    for cycle in project.module_cycles:
        members = set(cycle.modules)
        anchor = None
        source_module = None
        for resolution in project.import_resolutions:
            document_module = resolution.document.module
            candidate_source = document_module.name if document_module is not None else None
            if candidate_source not in members or resolution.import_.span is None:
                continue
            targets = {
                declaration.document.module.name
                for declaration in resolution.declarations
                if declaration.document.module is not None
                and declaration.document.module.name in members
            }
            if targets:
                anchor = resolution
                source_module = candidate_source
                break
        if anchor is None or source_module is None:
            continue
        rendered = ", ".join(cycle.modules)
        issues.append(
            ModuleValidationIssue(
                code="AIDL-R004",
                message=f"cyclic module dependency among modules [{rendered}]",
                source_path=anchor.document.source_path,
                location=anchor.import_.span,
                subject_name=source_module,
                expected="acyclic resolved module dependencies",
            )
        )
    return issues


def collect_module_validation_issues(
    project: CompilerProject,
) -> tuple[ModuleValidationIssue, ...]:
    """Return deterministic Module validation failures without re-owning imports."""

    return tuple((*_structure_issues(project), *_cycle_issues(project)))
