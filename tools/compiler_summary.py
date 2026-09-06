from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.compiler_diagnostics import CompilerAnalysis


MAX_SUMMARY_MODULES = 64
MAX_SUMMARY_DECLARATIONS = 128
MAX_SUMMARY_MODULE_DEPENDENCIES = 128


@dataclass(frozen=True)
class ProjectCount:
    kind: str
    count: int

    def to_json(self) -> dict[str, Any]:
        return {"count": self.count, "kind": self.kind}


@dataclass(frozen=True)
class ProjectModuleSummary:
    name: str
    document_count: int
    declaration_count: int
    exported_declaration_count: int
    declaration_kinds: tuple[ProjectCount, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "declarationCount": self.declaration_count,
            "declarationKinds": [item.to_json() for item in self.declaration_kinds],
            "documentCount": self.document_count,
            "exportedDeclarationCount": self.exported_declaration_count,
            "name": self.name,
        }


@dataclass(frozen=True)
class ProjectDeclarationSummary:
    fully_qualified_name: str
    kind: str
    exported: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "exported": self.exported,
            "fullyQualifiedName": self.fully_qualified_name,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class ProjectModuleDependencySummary:
    source_module: str
    target_module: str

    def to_json(self) -> dict[str, Any]:
        return {
            "sourceModule": self.source_module,
            "targetModule": self.target_module,
        }


@dataclass(frozen=True)
class ProjectSummary:
    document_count: int
    module_count: int
    declaration_count: int
    exported_declaration_count: int
    documents_without_module_count: int
    declaration_kinds: tuple[ProjectCount, ...]
    modules: tuple[ProjectModuleSummary, ...]
    declarations: tuple[ProjectDeclarationSummary, ...]
    module_dependencies: tuple[ProjectModuleDependencySummary, ...]
    total_module_count: int
    total_declaration_listing_count: int
    total_module_dependency_count: int
    modules_truncated: bool
    declarations_truncated: bool
    module_dependencies_truncated: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "declarationCount": self.declaration_count,
            "declarationKinds": [item.to_json() for item in self.declaration_kinds],
            "declarations": [item.to_json() for item in self.declarations],
            "documentCount": self.document_count,
            "documentsWithoutModuleCount": self.documents_without_module_count,
            "exportedDeclarationCount": self.exported_declaration_count,
            "moduleCount": self.module_count,
            "moduleDependencies": [item.to_json() for item in self.module_dependencies],
            "modules": [item.to_json() for item in self.modules],
            "totals": {
                "declarations": self.total_declaration_listing_count,
                "moduleDependencies": self.total_module_dependency_count,
                "modules": self.total_module_count,
            },
            "truncated": {
                "declarations": self.declarations_truncated,
                "moduleDependencies": self.module_dependencies_truncated,
                "modules": self.modules_truncated,
            },
        }


def _counts(kinds: list[str]) -> tuple[ProjectCount, ...]:
    counts: dict[str, int] = {}
    for kind in kinds:
        counts[kind] = counts.get(kind, 0) + 1
    return tuple(ProjectCount(kind=kind, count=counts[kind]) for kind in sorted(counts))


def summarize_project(analysis: CompilerAnalysis) -> ProjectSummary:
    """Project existing compiler-owned facts into a deterministic bounded agent summary."""

    project = analysis.project
    declaration_names = tuple(project.declaration_names)
    exported_count = sum(1 for item in declaration_names if item.declaration.exported)
    declaration_kinds = _counts([item.declaration.kind for item in declaration_names])

    module_summaries: list[ProjectModuleSummary] = []
    for module_name in sorted(project.modules):
        documents = project.modules[module_name]
        declarations = [
            item.declaration
            for item in declaration_names
            if item.document.module is not None and item.document.module.name == module_name
        ]
        module_summaries.append(
            ProjectModuleSummary(
                name=module_name,
                document_count=len(documents),
                declaration_count=len(declarations),
                exported_declaration_count=sum(1 for declaration in declarations if declaration.exported),
                declaration_kinds=_counts([declaration.kind for declaration in declarations]),
            )
        )

    declaration_summaries = sorted(
        (
            ProjectDeclarationSummary(
                fully_qualified_name=item.fully_qualified_name,
                kind=item.declaration.kind,
                exported=item.declaration.exported,
            )
            for item in declaration_names
            if item.fully_qualified_name is not None
        ),
        key=lambda item: (item.fully_qualified_name, item.kind, item.exported),
    )

    dependency_summaries = [
        ProjectModuleDependencySummary(source_module=source, target_module=target)
        for source, target in sorted(
            {
                (dependency.source_module, dependency.target_module)
                for dependency in project.module_dependencies
            }
        )
    ]

    return ProjectSummary(
        document_count=len(project.documents),
        module_count=len(project.modules),
        declaration_count=len(declaration_names),
        exported_declaration_count=exported_count,
        documents_without_module_count=len(project.documents_without_module),
        declaration_kinds=declaration_kinds,
        modules=tuple(module_summaries[:MAX_SUMMARY_MODULES]),
        declarations=tuple(declaration_summaries[:MAX_SUMMARY_DECLARATIONS]),
        module_dependencies=tuple(dependency_summaries[:MAX_SUMMARY_MODULE_DEPENDENCIES]),
        total_module_count=len(module_summaries),
        total_declaration_listing_count=len(declaration_summaries),
        total_module_dependency_count=len(dependency_summaries),
        modules_truncated=len(module_summaries) > MAX_SUMMARY_MODULES,
        declarations_truncated=len(declaration_summaries) > MAX_SUMMARY_DECLARATIONS,
        module_dependencies_truncated=len(dependency_summaries) > MAX_SUMMARY_MODULE_DEPENDENCIES,
    )
