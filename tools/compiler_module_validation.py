"""Stable Module document-structure validation over parser-preserved order."""
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


def collect_module_validation_issues(
    project: CompilerProject,
) -> tuple[ModuleValidationIssue, ...]:
    """Reject duplicate or misplaced Module declarations without re-owning M1 resolution."""

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
                        code="AIDL-R005",
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
                        code="AIDL-R005",
                        message=f"module '{module_name}' must appear before imports and declarations",
                        source_path=document.source_path,
                        location=node.span,
                        subject_name=module_name,
                        expected="leading module declaration before imports and declarations",
                    )
                )
            modules.append(node)
    return tuple(issues)
