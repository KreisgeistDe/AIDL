"""Compiler-facing source-model boundaries.

The active Breaking-Core P1 path projects the generic bootstrap ``Program`` shape
without consulting declaration-kind token tables. The legacy ``Node`` adapter is
retained only for the unmigrated P2+ corpus and is not language authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .aidl_parser import Node, Span
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from aidl_parser import Node, Span

from tools.core_bootstrap import Declaration as CoreDeclaration
from tools.core_bootstrap import Program as CoreProgram


@dataclass(frozen=True)
class CompilerModule:
    name: str | None
    span: Span | None = None
    end: Span | None = None


@dataclass(frozen=True)
class CompilerImport:
    name: str | None
    wildcard: bool = False
    span: Span | None = None
    end: Span | None = None


@dataclass(frozen=True)
class CompilerDeclaration:
    kind: str
    name: str | None
    exported: bool
    span: Span | None
    end: Span | None
    node: Any


@dataclass(frozen=True)
class CompilerDocument:
    source_path: Path
    span: Span | None
    end: Span | None
    module: CompilerModule | None
    imports: tuple[CompilerImport, ...]
    declarations: tuple[CompilerDeclaration, ...]
    top_level: tuple[Any, ...]


def compiler_document_from_core_program(source_path: Path, program: CoreProgram) -> CompilerDocument:
    """Project the active generic Core/bootstrap program into the compiler boundary.

    Declaration identity comes directly from each parsed declaration's TypeRef-derived
    ``kind`` value. No host declaration-kind registry participates in the projection.
    """
    aliases = dict(program.import_aliases)
    imports = tuple(
        CompilerImport(name=name, wildcard=False)
        for name in program.imports
    )
    declarations = tuple(
        CompilerDeclaration(
            kind=declaration.kind,
            name=declaration.name,
            exported=declaration.exported,
            span=None,
            end=None,
            node=declaration,
        )
        for declaration in program.declarations
    )
    return CompilerDocument(
        source_path=source_path,
        span=None,
        end=None,
        module=CompilerModule(program.module) if program.module is not None else None,
        imports=imports,
        declarations=declarations,
        top_level=tuple(program.declarations),
    )


def compiler_document_from_ast(source_path: Path, program: Node) -> CompilerDocument:
    """Legacy P2+ corpus adapter over the historical generic parser AST.

    This function is intentionally not used by the P1 Core authority path.
    """
    module: CompilerModule | None = None
    imports: list[CompilerImport] = []
    declarations: list[CompilerDeclaration] = []

    for child in program.children:
        if child.kind == "module":
            if module is None:
                module = CompilerModule(child.name, child.span, child.end)
            continue
        if child.kind == "import":
            imports.append(
                CompilerImport(
                    child.name,
                    bool(child.name and child.name.endswith(".*")),
                    child.span,
                    child.end,
                )
            )
            continue
        declarations.append(
            CompilerDeclaration(
                kind=child.kind,
                name=child.name,
                exported=bool(child.attrs.get("exported")),
                span=child.span,
                end=child.end,
                node=child,
            )
        )

    return CompilerDocument(
        source_path=source_path,
        span=program.span,
        end=program.end,
        module=module,
        imports=tuple(imports),
        declarations=tuple(declarations),
        top_level=tuple(program.children),
    )


__all__ = [
    "CompilerModule",
    "CompilerImport",
    "CompilerDeclaration",
    "CompilerDocument",
    "compiler_document_from_core_program",
    "compiler_document_from_ast",
]
