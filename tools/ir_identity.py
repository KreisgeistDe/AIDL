from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol


_FQN_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_-]*(\.[A-Za-z_][A-Za-z0-9_-]*)*$"
)


class _ModuleProjection(Protocol):
    name: str | None


class _DeclarationProjection(Protocol):
    name: str | None


class _DocumentProjection(Protocol):
    module: _ModuleProjection | None


class ResolvedDeclarationProjection(Protocol):
    """Structural view of one already-resolved compiler declaration projection."""

    document: _DocumentProjection
    declaration: _DeclarationProjection
    fully_qualified_name: str | None


@dataclass(frozen=True)
class IrDeclarationIdentity:
    """IR identity fields that do not depend on semantic hashing or IR emission."""

    declaration_id: str
    fqn: str
    name: str
    owner_module: str

    def as_ir_fields(self) -> dict[str, str]:
        """Return the schema-facing identity fields owned by M3-03."""

        return {
            "declarationId": self.declaration_id,
            "fqn": self.fqn,
            "name": self.name,
            "ownerModule": self.owner_module,
        }


class IrIdentityError(ValueError):
    """Raised when the resolved declaration projection cannot define IR identity."""


def _require_positive_major(major: int) -> int:
    if isinstance(major, bool) or not isinstance(major, int) or major < 1:
        raise IrIdentityError("declaration major version must be an explicit positive integer")
    return major


def declaration_identity(
    projection: ResolvedDeclarationProjection,
    major: int,
) -> IrDeclarationIdentity:
    """Derive stable IR identity from an existing resolved declaration projection.

    ``major`` is supplied explicitly by the caller because the source model does
    not currently expose an authoritative declaration major. This boundary does
    not invent an AIDL language version, resolve names, disambiguate duplicates,
    materialize defaults, compute semantic hashes, or emit complete IR.
    """

    major = _require_positive_major(major)
    fqn = projection.fully_qualified_name
    name = projection.declaration.name
    module = projection.document.module
    owner_module = module.name if module is not None else None

    if fqn is None:
        raise IrIdentityError("resolved declaration projection has no fully qualified name")
    if name is None:
        raise IrIdentityError("resolved declaration projection has no declaration name")
    if owner_module is None:
        raise IrIdentityError("resolved declaration projection has no owning module")
    if not _FQN_PATTERN.fullmatch(fqn):
        raise IrIdentityError(f"fully qualified name is not schema-compatible: {fqn!r}")
    if not _FQN_PATTERN.fullmatch(owner_module):
        raise IrIdentityError(f"owner module is not schema-compatible: {owner_module!r}")

    expected_fqn = f"{owner_module}.{name}"
    if fqn != expected_fqn:
        raise IrIdentityError(
            "resolved declaration projection is inconsistent: "
            f"expected {expected_fqn!r}, got {fqn!r}"
        )

    return IrDeclarationIdentity(
        declaration_id=f"{fqn}@{major}",
        fqn=fqn,
        name=name,
        owner_module=owner_module,
    )


def declaration_identities(
    projections: Iterable[ResolvedDeclarationProjection],
    major: int,
) -> tuple[IrDeclarationIdentity, ...]:
    """Project identities without collapsing or disambiguating duplicate FQNs."""

    major = _require_positive_major(major)
    return tuple(declaration_identity(projection, major) for projection in projections)
