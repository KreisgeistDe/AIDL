"""Typed compiler-facing document boundary over the generic parser AST.

This module intentionally does not perform module loading, import resolution,
name resolution, semantic validation, or any IntelliJ/PSI integration. It only
projects the parser's top-level ``Node`` structure into stable typed document,
module, import, and declaration-header records while retaining every original
parser node.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from .aidl_parser import Node, Span
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from aidl_parser import Node, Span


@dataclass(frozen=True)
class CompilerModule:
    """Syntactic module declaration extracted from a parsed document."""

    name: str | None
    span: Span | None
    end: Span | None


@dataclass(frozen=True)
class CompilerImport:
    """Syntactic import declaration without resolution semantics."""

    name: str | None
    wildcard: bool
    span: Span | None
    end: Span | None


@dataclass(frozen=True)
class CompilerDeclaration:
    """Typed syntactic header for one top-level declaration."""

    kind: str
    name: str | None
    exported: bool
    span: Span | None
    end: Span | None
    node: Node


@dataclass(frozen=True)
class CompilerDocument:
    """Smallest typed compiler boundary for one parsed source document."""

    source_path: Path
    span: Span | None
    end: Span | None
    module: CompilerModule | None
    imports: tuple[CompilerImport, ...]
    declarations: tuple[CompilerDeclaration, ...]
    top_level: tuple[Node, ...]


def compiler_document_from_ast(source_path: Path, program: Node) -> CompilerDocument:
    """Project a parser ``program`` node into the typed compiler boundary.

    Extraction preserves parser order and parser-produced source locations. No
    semantic validity is inferred: the first syntactic module declaration is
    exposed through ``module`` and every original top-level node remains in
    ``top_level`` so later validation can diagnose unusual/invalid structures
    without information loss.
    """

    module: CompilerModule | None = None
    imports: list[CompilerImport] = []
    declarations: list[CompilerDeclaration] = []

    for child in program.children:
        if child.kind == "module":
            if module is None:
                module = CompilerModule(
                    name=child.name,
                    span=child.span,
                    end=child.end,
                )
            continue
        if child.kind == "import":
            imports.append(
                CompilerImport(
                    name=child.name,
                    wildcard=bool(child.name and child.name.endswith(".*")),
                    span=child.span,
                    end=child.end,
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
