"""Deterministic project loading, import resolution, module dependencies, and symbols.

This module groups parsed compiler documents by their declared module name,
projects top-level declaration names into fully qualified names, resolves
explicit and wildcard imports over exported project declarations, derives
cyclic module dependencies from those existing import resolutions, and builds
a deterministic declaration/operation symbol table. It does not perform
semantic validation or diagnostic production.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

try:
    from .aidl_parser import iter_aidl_files, parse_text
    from .compiler_ast import (
        CompilerDeclaration,
        CompilerDocument,
        CompilerImport,
        compiler_document_from_ast,
    )
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from aidl_parser import iter_aidl_files, parse_text
    from compiler_ast import (
        CompilerDeclaration,
        CompilerDocument,
        CompilerImport,
        compiler_document_from_ast,
    )


OPERATION_DECLARATION_KINDS = frozenset(
    {"policy", "query", "mutation", "workflow", "saga", "task"}
)


@dataclass(frozen=True)
class CompilerDeclarationName:
    """One declaration and its syntactically derivable fully qualified name."""

    document: CompilerDocument
    declaration: CompilerDeclaration
    fully_qualified_name: str | None


@dataclass(frozen=True)
class CompilerImportResolution:
    """One syntactic import and the exported declarations it deterministically resolves."""

    document: CompilerDocument
    import_: CompilerImport
    declarations: tuple[CompilerDeclarationName, ...]


@dataclass(frozen=True)
class CompilerModuleDependency:
    """One resolved module-to-module dependency derived from import semantics."""

    source_module: str
    target_module: str


@dataclass(frozen=True)
class CompilerModuleCycle:
    """One deterministic strongly connected group of cyclic modules."""

    modules: tuple[str, ...]


@dataclass(frozen=True)
class CompilerSymbolTable:
    """Deterministic declaration and module-scoped operation lookup tables."""

    declarations_by_fqn: Mapping[str, tuple[CompilerDeclarationName, ...]]
    operations_by_module: Mapping[
        str, Mapping[str, tuple[CompilerDeclarationName, ...]]
    ]

    def lookup_declarations(
        self, fully_qualified_name: str
    ) -> tuple[CompilerDeclarationName, ...]:
        """Return all declarations for an FQN in stable project order."""

        return self.declarations_by_fqn.get(fully_qualified_name, ())

    def lookup_operations(
        self, module_name: str, operation_name: str
    ) -> tuple[CompilerDeclarationName, ...]:
        """Return operation declarations for one module-local operation name."""

        module_operations = self.operations_by_module.get(module_name)
        if module_operations is None:
            return ()
        return module_operations.get(operation_name, ())


@dataclass(frozen=True)
class CompilerProject:
    """Ordered compiler documents plus deterministic project projections."""

    documents: tuple[CompilerDocument, ...]
    modules: Mapping[str, tuple[CompilerDocument, ...]]
    documents_without_module: tuple[CompilerDocument, ...]
    declaration_names: tuple[CompilerDeclarationName, ...]
    symbol_table: CompilerSymbolTable
    import_resolutions: tuple[CompilerImportResolution, ...]
    module_dependencies: tuple[CompilerModuleDependency, ...]
    module_cycles: tuple[CompilerModuleCycle, ...]


def _build_symbol_table(
    declaration_names: tuple[CompilerDeclarationName, ...],
) -> CompilerSymbolTable:
    """Build stable lookups without resolving duplicate/ambiguous symbols."""

    declarations_by_fqn: dict[str, list[CompilerDeclarationName]] = {}
    operations_by_module: dict[
        str, dict[str, list[CompilerDeclarationName]]
    ] = {}

    for declaration_name in declaration_names:
        fully_qualified_name = declaration_name.fully_qualified_name
        if fully_qualified_name is not None:
            declarations_by_fqn.setdefault(fully_qualified_name, []).append(
                declaration_name
            )

        declaration = declaration_name.declaration
        module = declaration_name.document.module
        if (
            module is None
            or module.name is None
            or declaration.name is None
            or declaration.kind not in OPERATION_DECLARATION_KINDS
        ):
            continue
        operations_by_module.setdefault(module.name, {}).setdefault(
            declaration.name, []
        ).append(declaration_name)

    immutable_declarations = MappingProxyType(
        {
            fully_qualified_name: tuple(matches)
            for fully_qualified_name, matches in declarations_by_fqn.items()
        }
    )
    immutable_operations = MappingProxyType(
        {
            module_name: MappingProxyType(
                {
                    operation_name: tuple(matches)
                    for operation_name, matches in module_operations.items()
                }
            )
            for module_name, module_operations in operations_by_module.items()
        }
    )
    return CompilerSymbolTable(
        declarations_by_fqn=immutable_declarations,
        operations_by_module=immutable_operations,
    )


def _find_module_cycles(
    module_names: tuple[str, ...],
    dependencies: tuple[CompilerModuleDependency, ...],
) -> tuple[CompilerModuleCycle, ...]:
    """Return cyclic strongly connected module groups in stable module order."""

    adjacency: dict[str, list[str]] = {module_name: [] for module_name in module_names}
    self_dependencies: set[str] = set()
    for dependency in dependencies:
        adjacency[dependency.source_module].append(dependency.target_module)
        if dependency.source_module == dependency.target_module:
            self_dependencies.add(dependency.source_module)

    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []
    module_order = {module_name: position for position, module_name in enumerate(module_names)}

    def visit(module_name: str) -> None:
        nonlocal index
        indices[module_name] = index
        lowlinks[module_name] = index
        index += 1
        stack.append(module_name)
        on_stack.add(module_name)

        for target_module in adjacency[module_name]:
            if target_module not in indices:
                visit(target_module)
                lowlinks[module_name] = min(
                    lowlinks[module_name], lowlinks[target_module]
                )
            elif target_module in on_stack:
                lowlinks[module_name] = min(
                    lowlinks[module_name], indices[target_module]
                )

        if lowlinks[module_name] != indices[module_name]:
            return

        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == module_name:
                break
        component.sort(key=module_order.__getitem__)
        if len(component) > 1 or component[0] in self_dependencies:
            components.append(tuple(component))

    for module_name in module_names:
        if module_name not in indices:
            visit(module_name)

    components.sort(key=lambda component: module_order[component[0]])
    return tuple(CompilerModuleCycle(modules=component) for component in components)


def compiler_project_from_documents(
    documents: Iterable[CompilerDocument],
) -> CompilerProject:
    """Index documents and resolve imports without changing supplied source order."""

    ordered_documents = tuple(documents)
    modules: dict[str, list[CompilerDocument]] = {}
    documents_without_module: list[CompilerDocument] = []
    declaration_names: list[CompilerDeclarationName] = []

    for document in ordered_documents:
        module_name = document.module.name if document.module is not None else None
        if module_name is None:
            documents_without_module.append(document)
        else:
            modules.setdefault(module_name, []).append(document)

        for declaration in document.declarations:
            fully_qualified_name = None
            if module_name is not None and declaration.name is not None:
                fully_qualified_name = f"{module_name}.{declaration.name}"
            declaration_names.append(
                CompilerDeclarationName(
                    document=document,
                    declaration=declaration,
                    fully_qualified_name=fully_qualified_name,
                )
            )

    declaration_name_tuple = tuple(declaration_names)
    symbol_table = _build_symbol_table(declaration_name_tuple)

    exported_by_fqn: dict[str, list[CompilerDeclarationName]] = {}
    exported_by_module: dict[str, list[CompilerDeclarationName]] = {}
    for declaration_name in declaration_names:
        if (
            not declaration_name.declaration.exported
            or declaration_name.fully_qualified_name is None
        ):
            continue
        exported_by_fqn.setdefault(declaration_name.fully_qualified_name, []).append(
            declaration_name
        )
        module_name = (
            declaration_name.document.module.name
            if declaration_name.document.module is not None
            else None
        )
        if module_name is not None:
            exported_by_module.setdefault(module_name, []).append(declaration_name)

    import_resolutions: list[CompilerImportResolution] = []
    for document in ordered_documents:
        for import_ in document.imports:
            resolved: tuple[CompilerDeclarationName, ...] = ()
            if import_.name is not None:
                if import_.wildcard and import_.name.endswith(".*"):
                    module_name = import_.name[:-2]
                    resolved = tuple(exported_by_module.get(module_name, ()))
                elif not import_.wildcard:
                    resolved = tuple(exported_by_fqn.get(import_.name, ()))
            import_resolutions.append(
                CompilerImportResolution(
                    document=document,
                    import_=import_,
                    declarations=resolved,
                )
            )

    module_dependencies: list[CompilerModuleDependency] = []
    seen_dependencies: set[tuple[str, str]] = set()
    for resolution in import_resolutions:
        source_module = (
            resolution.document.module.name
            if resolution.document.module is not None
            else None
        )
        if source_module is None:
            continue
        for declaration in resolution.declarations:
            target_module = (
                declaration.document.module.name
                if declaration.document.module is not None
                else None
            )
            if target_module is None:
                continue
            dependency_key = (source_module, target_module)
            if dependency_key in seen_dependencies:
                continue
            seen_dependencies.add(dependency_key)
            module_dependencies.append(
                CompilerModuleDependency(
                    source_module=source_module,
                    target_module=target_module,
                )
            )

    immutable_modules = MappingProxyType(
        {name: tuple(module_documents) for name, module_documents in modules.items()}
    )
    dependencies = tuple(module_dependencies)
    return CompilerProject(
        documents=ordered_documents,
        modules=immutable_modules,
        documents_without_module=tuple(documents_without_module),
        declaration_names=declaration_name_tuple,
        symbol_table=symbol_table,
        import_resolutions=tuple(import_resolutions),
        module_dependencies=dependencies,
        module_cycles=_find_module_cycles(tuple(modules), dependencies),
    )


def load_compiler_project(paths: Iterable[Path]) -> CompilerProject:
    """Discover and parse project sources, then build the deterministic index."""

    documents = []
    for source_path in iter_aidl_files(list(paths)):
        program, _, _ = parse_text(source_path.read_text(encoding="utf-8"))
        documents.append(compiler_document_from_ast(source_path, program))
    return compiler_project_from_documents(documents)
