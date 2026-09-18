from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.core_bootstrap import Program, parse_bootstrap_source
from tools.core_self_description import (
    CoreSelfDescriptionError,
    SelfDescribedCore,
    compile_self_described_core,
    semantic_meta_ir_text,
)
from tools.core_semantics import CoreContractError, load_semantic_registry, validate_source


class CoreLanguageError(ValueError):
    """Raised when the P1 authority/bootstrap boundary is inconsistent."""


@dataclass(frozen=True)
class CoreAuthority:
    kernel: dict[str, Any]
    core_source: str
    core: SelfDescribedCore


_REQUIRED_KERNEL_OWNS = {
    "universal-declaration-envelope",
    "generic-parameters",
    "recursive-generic-nullable-type-ref-syntax",
    "body-entry-framing-and-continuation",
    "modifier-call-tokenization",
    "finite-structural-meta-combinators",
}
_FORBIDDEN_KERNEL_AUTHORITY = {
    "concrete-declaration-kind-catalog",
    "domain-declaration-catalog",
    "concrete-category-to-schema-map",
    "concrete-modifier-catalog",
    "core-base-type-name-catalog",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_kernel_contract(text: str | None = None) -> dict[str, Any]:
    if text is None:
        text = (_root() / "spec" / "bootstrap-kernel-v1.json").read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CoreLanguageError(f"bootstrap kernel is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CoreLanguageError("bootstrap kernel must be an object")
    if value.get("kernelVersion") != 1:
        raise CoreLanguageError("bootstrap kernelVersion must be 1")
    owns = value.get("owns")
    excludes = value.get("excludes")
    if not isinstance(owns, list) or not all(isinstance(item, str) for item in owns):
        raise CoreLanguageError("bootstrap owns must be a string list")
    if not isinstance(excludes, list) or not all(isinstance(item, str) for item in excludes):
        raise CoreLanguageError("bootstrap excludes must be a string list")
    missing = sorted(_REQUIRED_KERNEL_OWNS - set(owns))
    if missing:
        raise CoreLanguageError("bootstrap is missing required structural ownership: " + ", ".join(missing))
    leaked = sorted(_FORBIDDEN_KERNEL_AUTHORITY & set(owns))
    if leaked:
        raise CoreLanguageError("bootstrap illegally owns Core language authority: " + ", ".join(leaked))
    missing_exclusions = sorted(_FORBIDDEN_KERNEL_AUTHORITY - set(excludes))
    if missing_exclusions:
        raise CoreLanguageError("bootstrap must explicitly exclude host language catalogs: " + ", ".join(missing_exclusions))
    firewall = value.get("authorityFirewall")
    if not isinstance(firewall, dict) or firewall.get("concreteDeclarationKindCatalogOwnedByHost") is not False:
        raise CoreLanguageError("bootstrap authority firewall must forbid a host declaration-kind catalog")
    if firewall.get("separateHostTypeHierarchy") is not False:
        raise CoreLanguageError("bootstrap authority firewall must forbid a separate host type hierarchy")
    return value


def load_core_authority(*, kernel_text: str | None = None, core_source: str | None = None) -> CoreAuthority:
    kernel = load_kernel_contract(kernel_text)
    if core_source is None:
        core_source = (_root() / "spec" / "core-self-description-v1.aidl").read_text(encoding="utf-8")
    try:
        core = compile_self_described_core(core_source)
    except CoreSelfDescriptionError as exc:
        raise CoreLanguageError(str(exc)) from exc
    return CoreAuthority(kernel, core_source, core)


def parse_core_language_source(source: str, *, authority: CoreAuthority | None = None) -> Program:
    """Parse the active language with the finite generic bootstrap grammar only.

    No declaration-kind token table from tools.aidl_parser participates in this path.
    Concrete kind/slot meaning is validated from Core metadata separately.
    """
    if authority is None:
        authority = load_core_authority()
    try:
        return parse_bootstrap_source(source)
    except Exception as exc:
        raise CoreLanguageError(str(exc)) from exc


def validate_core_language_source(source: str, *, authority: CoreAuthority | None = None) -> tuple[Any, ...]:
    """Validate source against semantics derived exactly from the direct Core authority."""
    if authority is None:
        authority = load_core_authority()
    parse_core_language_source(source, authority=authority)
    try:
        registry = load_semantic_registry(
            direct_source=authority.core_source,
            meta_ir_text=semantic_meta_ir_text(authority.core_source),
        )
        return validate_source(source, registry)
    except (CoreContractError, CoreSelfDescriptionError) as exc:
        raise CoreLanguageError(str(exc)) from exc


def core_source_sha256(authority: CoreAuthority | None = None) -> str:
    if authority is None:
        authority = load_core_authority()
    return hashlib.sha256(authority.core_source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def grammar_projection(authority: CoreAuthority | None = None) -> str:
    """Return the deterministic human-readable grammar projection embedded in docs/06-grammar.md."""
    if authority is None:
        authority = load_core_authority()
    kinds = ", ".join(sorted(set(authority.core.contracts) | set(authority.core.aliases)))
    return "\n".join(
        [
            "<!-- BEGIN GENERATED CORE GRAMMAR -->",
            f"Core source SHA-256: `{core_source_sha256(authority)}`",
            "",
            "```ebnf",
            "program        = moduleDirective { importDirective } { declaration } ;",
            "moduleDirective= \"module\" qualifiedName statementEnd ;",
            "importDirective= \"import\" qualifiedName [ \"as\" identifier ] statementEnd ;",
            "declaration    = [ \"export\" ] typeRef identifier [ genericParameters ]",
            "                 [ namedArguments ] [ \"->\" typeRef ] [ declarationBody ] statementEnd? ;",
            "namedArguments = \"(\" namedArgument { \",\" namedArgument } \")\" ;",
            "namedArgument  = identifier [ \"?\" ] \":\" ( typeRef | value ) ;",
            "declarationBody= \"{\" { bodyEntry } \"}\" ;",
            "bodyEntry      = qualifiedName [ identifier ] [ \":\" value ] { modifierCall } statementEnd? ;",
            "modifierCall   = \"@\" identifier [ \"(\" [ modifierArgument { \",\" modifierArgument } ] \")\" ] ;",
            "modifierArgument = [ identifier \":\" ] value ;",
            "typeRef        = qualifiedName [ \"<\" typeRef { \",\" typeRef } \">\" ] [ \"?\" ] ;",
            "```",
            "",
            "Concrete declaration contracts are read from `spec/core-self-description-v1.aidl`;",
            "the Bootstrap Kernel owns only the finite structural syntax above.",
            f"Current Core-declared kinds/aliases: {kinds}.",
            "<!-- END GENERATED CORE GRAMMAR -->",
        ]
    )


def check_grammar_projection(path: Path | None = None) -> None:
    if path is None:
        path = _root() / "docs" / "06-grammar.md"
    text = path.read_text(encoding="utf-8")
    begin = "<!-- BEGIN GENERATED CORE GRAMMAR -->"
    end = "<!-- END GENERATED CORE GRAMMAR -->"
    if begin not in text or end not in text:
        raise CoreLanguageError("grammar projection markers are missing")
    actual = text[text.index(begin) : text.index(end) + len(end)]
    expected = grammar_projection()
    if actual != expected:
        raise CoreLanguageError("Core grammar projection drift: regenerate docs/06-grammar.md from tools.core_language.grammar_projection()")


__all__ = [
    "CoreAuthority",
    "CoreLanguageError",
    "load_kernel_contract",
    "load_core_authority",
    "parse_core_language_source",
    "validate_core_language_source",
    "grammar_projection",
    "check_grammar_projection",
]
