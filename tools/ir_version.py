from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


CURRENT_IR_VERSION = "0.3.0"
_VERSION_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_PROFILE_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


class IrCompatibilityError(ValueError):
    """Raised when an IR document cannot be consumed safely."""


@dataclass(frozen=True, order=True)
class IrVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: object) -> "IrVersion":
        if not isinstance(value, str):
            raise IrCompatibilityError("irVersion must be a string")
        match = _VERSION_PATTERN.fullmatch(value)
        if match is None:
            raise IrCompatibilityError(
                "irVersion must be an exact major.minor.patch numeric version"
            )
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class IrConsumerCapabilities:
    """Version/profile capabilities declared by one IR consumer."""

    ir_version: IrVersion
    profile_majors: frozenset[tuple[str, int]] = frozenset()
    tolerated_additive_fields: frozenset[str] = frozenset()

    @classmethod
    def create(
        cls,
        ir_version: str,
        *,
        profile_majors: Iterable[tuple[str, int]] = (),
        tolerated_additive_fields: Iterable[str] = (),
    ) -> "IrConsumerCapabilities":
        profiles: set[tuple[str, int]] = set()
        for profile_id, major in profile_majors:
            if not isinstance(profile_id, str) or _PROFILE_PATTERN.fullmatch(profile_id) is None:
                raise IrCompatibilityError(f"invalid profile id: {profile_id!r}")
            if isinstance(major, bool) or not isinstance(major, int) or major < 1:
                raise IrCompatibilityError(
                    f"profile major for {profile_id!r} must be a positive integer"
                )
            profiles.add((profile_id, major))

        fields: set[str] = set()
        for path in tolerated_additive_fields:
            if not isinstance(path, str) or not path.startswith("/") or path == "/":
                raise IrCompatibilityError(
                    "tolerated additive fields must be non-root JSON-pointer paths"
                )
            fields.add(path)
        return cls(IrVersion.parse(ir_version), frozenset(profiles), frozenset(fields))


def _profile_set(value: object) -> frozenset[tuple[str, int]]:
    if not isinstance(value, list):
        raise IrCompatibilityError("profiles must be an array")
    profiles: set[tuple[str, int]] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise IrCompatibilityError(f"profiles/{index} must be an object")
        profile_id = item.get("id")
        major = item.get("major")
        if not isinstance(profile_id, str) or _PROFILE_PATTERN.fullmatch(profile_id) is None:
            raise IrCompatibilityError(f"profiles/{index}/id is invalid")
        if isinstance(major, bool) or not isinstance(major, int) or major < 1:
            raise IrCompatibilityError(f"profiles/{index}/major must be a positive integer")
        profile = (profile_id, major)
        if profile in profiles:
            raise IrCompatibilityError(f"duplicate profile capability: {profile_id}@{major}")
        profiles.add(profile)
    return frozenset(profiles)


def require_compatible_ir(
    document: Mapping[str, Any],
    consumer: IrConsumerCapabilities,
    *,
    additive_fields: Iterable[str] = (),
) -> None:
    """Reject IR that the declared consumer cannot safely understand.

    A newer producer minor is accepted only when every field introduced beyond
    the consumer's minor is explicitly named by both the producer projection
    and the consumer capability manifest. Patch versions are compatible within
    one major/minor line. Profile major versions are independent capabilities.
    """

    if not isinstance(document, Mapping):
        raise IrCompatibilityError("IR document must be an object")
    producer = IrVersion.parse(document.get("irVersion"))
    if producer.major != consumer.ir_version.major:
        raise IrCompatibilityError(
            f"incompatible IR major: producer {producer.major}, consumer {consumer.ir_version.major}"
        )

    actual_additions = frozenset(additive_fields)
    for path in actual_additions:
        if not isinstance(path, str) or not path.startswith("/") or path == "/":
            raise IrCompatibilityError("additive fields must be non-root JSON-pointer paths")
    if producer.minor > consumer.ir_version.minor:
        unsupported = sorted(actual_additions - consumer.tolerated_additive_fields)
        if unsupported:
            raise IrCompatibilityError(
                "unsupported additive IR fields: " + ", ".join(unsupported)
            )

    unknown_profiles = sorted(_profile_set(document.get("profiles")) - consumer.profile_majors)
    if unknown_profiles:
        rendered = ", ".join(f"{profile_id}@{major}" for profile_id, major in unknown_profiles)
        raise IrCompatibilityError("unsupported profile majors: " + rendered)
