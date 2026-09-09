"""M16.5 E5 isolated old-to-candidate migration/formatting experiment.

This module is experimental evidence only. It does not change production AIDL
syntax, parser acceptance, formatter behavior, Canonical IR, or support claims.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from typing import Any, Iterable

from tools.aidl_parser import parse_text
from tools.m16_5_e3_prototype import CANDIDATE_SCHEMA_VERSION as E3_VERSION
from tools.m16_5_e3_prototype import parse_candidate as parse_e3_candidate

OLD_SCHEMA_ID = "urn:aidl:schema:language:m16.5-e5-current"
OLD_VERSION = "m16.5-e5-current-v1"
TARGET_SCHEMA_ID = "urn:aidl:schema:language:m16.5-e5-candidate"
TARGET_VERSION = "m16.5-e5-candidate-v1"

ROW_IDS = (
    "projection-relationship",
    "client-target",
    "migration-source-target",
    "consumer-relationship",
    "explicit-field-child",
    "explicit-index",
    "queue-deadletter",
    "schedule-lease",
    "sync-outbox",
)

_SCHEMA_PAYLOAD = {
    "old": {"id": OLD_SCHEMA_ID, "version": OLD_VERSION, "rows": ROW_IDS},
    "target": {"id": TARGET_SCHEMA_ID, "version": TARGET_VERSION, "rows": ROW_IDS},
}
OLD_SCHEMA_FINGERPRINT = "sha256:" + hashlib.sha256(
    json.dumps(_SCHEMA_PAYLOAD["old"], sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
TARGET_SCHEMA_FINGERPRINT = "sha256:" + hashlib.sha256(
    json.dumps(_SCHEMA_PAYLOAD["target"], sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    offset: int = 0


class MigrationError(ValueError):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(f"{diagnostic.code}: {diagnostic.message}")
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    row_id: str
    role: str
    start: int
    end: int


@dataclass(frozen=True)
class LosslessSidecar:
    source: str
    source_fingerprint: str
    source_version: str
    schema_fingerprint: str
    anchors: tuple[Anchor, ...]


@dataclass(frozen=True)
class Edit:
    anchor_id: str
    row_id: str
    start: int
    end: int
    replacement: str


@dataclass(frozen=True)
class Relocation:
    anchor_id: str
    old_start: int
    old_end: int
    new_start: int
    new_end: int


@dataclass(frozen=True)
class SemanticFact:
    row_id: str
    identity: str
    facts: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class MigrationPlan:
    source_version: str
    old_version: str
    target_version: str
    old_schema_fingerprint: str
    target_schema_fingerprint: str
    source_fingerprint: str
    edits: tuple[Edit, ...]
    relocations: tuple[Relocation, ...]
    semantic_result: str
    old_facts: tuple[SemanticFact, ...]
    target_facts: tuple[SemanticFact, ...]
    rollback_source: str
    e3_replayed_rows: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class MigrationResult:
    source: str
    plan: MigrationPlan


@dataclass(frozen=True)
class _Rule:
    row_id: str
    role: str
    old_re: re.Pattern[str]
    candidate_re: re.Pattern[str]


def _rx(pattern: str, flags: int = re.MULTILINE) -> re.Pattern[str]:
    return re.compile(pattern, flags)


RULES = (
    _Rule(
        "projection-relationship",
        "declaration-header",
        _rx(r"^(?P<i>[ \t]*)projection[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+from[ \t]+\[(?P<sources>[^\]\n]+)\][ \t]+into[ \t]+(?P<target>[A-Za-z_][\w.]*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]*)projection[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P=i)  source:[ \t]*(?P<source>[A-Za-z_][\w.]*)\n(?P=i)  target:[ \t]*(?P<target>[A-Za-z_][\w.]*)$"),
    ),
    _Rule(
        "client-target",
        "declaration-header",
        _rx(r"^(?P<i>[ \t]*)client[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+for[ \t]+(?P<service>[A-Za-z_][\w.]*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]*)client[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P=i)  service:[ \t]*(?P<service>[A-Za-z_][\w.]*)$"),
    ),
    _Rule(
        "migration-source-target",
        "declaration-header",
        _rx(r'^(?P<i>[ \t]*)migration[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+from[ \t]+(?P<from>"(?:\\.|[^"\\])*")[ \t]+to[ \t]+(?P<to>"(?:\\.|[^"\\])*")[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$'),
        _rx(r'^(?P<i>[ \t]*)migration[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P=i)  from:[ \t]*(?P<from>"(?:\\.|[^"\\])*")\n(?P=i)  to:[ \t]*(?P<to>"(?:\\.|[^"\\])*")$'),
    ),
    _Rule(
        "consumer-relationship",
        "declaration-header",
        _rx(r"^(?P<i>[ \t]*)consumer[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]+on[ \t]+(?P<topic>[A-Za-z_][\w.]*)[ \t]+from[ \t]+(?P<source>[A-Za-z_][\w.]*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]*)consumer[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\{(?P<tail>[ \t]*(?://[^\n]*)?)\n(?P=i)  topic:[ \t]*(?P<topic>[A-Za-z_][\w.]*)\n(?P=i)  source:[ \t]*(?P<source>[A-Za-z_][\w.]*)$"),
    ),
    _Rule(
        "explicit-field-child",
        "body-entry",
        _rx(r"^(?P<i>[ \t]+)(?!field\b)(?P<name>[A-Za-z_]\w*)[ \t]*:[ \t]*(?P<type>[A-Za-z_][\w.<>\[\]?]*)?(?P<mods>(?:[ \t]+[^/\n]+?)?)(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]+)field[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*:[ \t]*(?P<type>[A-Za-z_][\w.<>\[\]?]*)(?P<mods>(?:[ \t]+[^/\n]+?)?)(?P<tail>[ \t]*(?://[^\n]*)?)$"),
    ),
    _Rule(
        "explicit-index",
        "body-entry",
        _rx(r"^(?P<i>[ \t]+)index[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*\((?P<fields>[^)\n]+)\)(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]+)index[ \t]+(?P<name>[A-Za-z_]\w*)[ \t]*:[ \t]*\((?P<fields>[^)\n]+)\)(?P<tail>[ \t]*(?://[^\n]*)?)$"),
    ),
    _Rule(
        "queue-deadletter",
        "body-entry",
        _rx(r"^(?P<i>[ \t]+)deadLetter[ \t]+after[ \t]+(?P<count>\d+)[ \t]+attempts(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]+)deadLetter[ \t]*:[ \t]*(?P<count>\d+)[ \t]+attempts(?P<tail>[ \t]*(?://[^\n]*)?)$"),
    ),
    _Rule(
        "schedule-lease",
        "body-entry",
        _rx(r"^(?P<i>[ \t]+)singleton[ \t]+lease[ \t]+(?P<duration>\d+(?:\.\d+)?(?:ms|s|m|h|d))(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]+)singleton[ \t]*:[ \t]*lease[ \t]+(?P<duration>\d+(?:\.\d+)?(?:ms|s|m|h|d))(?P<tail>[ \t]*(?://[^\n]*)?)$"),
    ),
    _Rule(
        "sync-outbox",
        "body-entry",
        _rx(r"^(?P<i>[ \t]+)changes[ \t]+to[ \t]+(?P<target>[A-Za-z_][\w.]*)[ \t]+via[ \t]+outbox(?P<tail>[ \t]*(?://[^\n]*)?)$"),
        _rx(r"^(?P<i>[ \t]+)changes[ \t]*:[ \t]*(?P<target>[A-Za-z_][\w.]*)[ \t]+via[ \t]+outbox(?P<tail>[ \t]*(?://[^\n]*)?)$"),
    ),
)


def source_fingerprint(source: str) -> str:
    return "sha256:" + hashlib.sha256(source.encode()).hexdigest()


def _fail(code: str, message: str, offset: int = 0) -> None:
    raise MigrationError(Diagnostic(code, message, offset))


def _matches(source: str, *, candidate: bool) -> Iterable[tuple[_Rule, re.Match[str]]]:
    for rule in RULES:
        pattern = rule.candidate_re if candidate else rule.old_re
        for match in pattern.finditer(source):
            if rule.row_id == "explicit-field-child":
                prefix = source[: match.start()]
                opener = prefix.rfind("entity ")
                close = prefix.rfind("}")
                if opener < 0 or opener < close:
                    continue
            yield rule, match


def build_sidecar(
    source: str,
    *,
    source_version: str,
    schema_fingerprint: str,
) -> LosslessSidecar:
    if source_version == OLD_VERSION:
        candidate = False
        expected_schema = OLD_SCHEMA_FINGERPRINT
    elif source_version == TARGET_VERSION:
        candidate = True
        expected_schema = TARGET_SCHEMA_FINGERPRINT
    else:
        _fail("AIDL-S008", f"unknown source version {source_version!r}")
    if schema_fingerprint != expected_schema:
        _fail("AIDL-S008", "source/schema fingerprint mismatch")
    anchors = []
    counts: dict[str, int] = {}
    for rule, match in _matches(source, candidate=candidate):
        index = counts.get(rule.row_id, 0)
        counts[rule.row_id] = index + 1
        anchors.append(
            Anchor(
                f"{rule.row_id}:{index}",
                rule.row_id,
                rule.role,
                match.start(),
                match.end(),
            )
        )
    return LosslessSidecar(
        source,
        source_fingerprint(source),
        source_version,
        schema_fingerprint,
        tuple(anchors),
    )


def _clean_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _index_fields(value: str) -> tuple[tuple[str, str], ...]:
    out = []
    for raw in _clean_csv(value):
        bits = raw.split()
        if len(bits) == 1:
            out.append((bits[0], "default"))
        elif len(bits) == 2 and bits[1] in {"asc", "desc"}:
            out.append((bits[0], bits[1]))
        else:
            _fail("AIDL-S004", f"unsupported bounded index field {raw!r}")
    return tuple(out)


def _fact(rule: _Rule, match: re.Match[str], source: str, *, candidate: bool) -> SemanticFact:
    g = match.groupdict()
    row = rule.row_id
    if row == "projection-relationship":
        sources = (g["source"],) if candidate else _clean_csv(g["sources"])
        facts = (("sources", sources), ("target", g["target"]))
        identity = g["name"]
    elif row == "client-target":
        identity = g["name"]
        facts = (("service", g["service"]),)
    elif row == "migration-source-target":
        identity = g["name"]
        facts = (("from", g["from"][1:-1]), ("to", g["to"][1:-1]))
    elif row == "consumer-relationship":
        identity = g["name"]
        facts = (("topic", g["topic"]), ("source", g["source"]))
    elif row == "explicit-field-child":
        identity = g["name"]
        mods = tuple((g.get("mods") or "").strip().split())
        facts = (("type", g["type"]), ("modifiers", mods))
    elif row == "explicit-index":
        identity = g["name"]
        facts = (("fields", _index_fields(g["fields"])),)
    elif row == "queue-deadletter":
        identity = _enclosing_name(source, match.start(), ("queue", "topic"))
        facts = (
            ("attempts", int(g["count"])),
            ("owner_kind", _enclosing_kind(source, match.start(), ("queue", "topic"))),
        )
    elif row == "schedule-lease":
        identity = _enclosing_name(source, match.start(), ("schedule",))
        facts = (("mode", "singleton"), ("lease", g["duration"]))
    elif row == "sync-outbox":
        identity = _enclosing_name(source, match.start(), ("sync",))
        facts = (("target", g["target"]), ("delivery", "outbox"))
    else:
        raise AssertionError(row)
    return SemanticFact(row, identity, tuple(facts))


def _enclosing(source: str, offset: int, kinds: tuple[str, ...]) -> re.Match[str]:
    prefix = source[:offset]
    pattern = re.compile(
        r"(?m)^(?P<i>[ \t]*)(?P<kind>"
        + "|".join(map(re.escape, kinds))
        + r")[ \t]+(?P<name>[A-Za-z_]\w*)\b[^{\n]*\{"
    )
    matches = list(pattern.finditer(prefix))
    if not matches:
        _fail("AIDL-S005", f"cannot resolve enclosing {'/'.join(kinds)} declaration", offset)
    return matches[-1]


def _enclosing_name(source: str, offset: int, kinds: tuple[str, ...]) -> str:
    return _enclosing(source, offset, kinds).group("name")


def _enclosing_kind(source: str, offset: int, kinds: tuple[str, ...]) -> str:
    return _enclosing(source, offset, kinds).group("kind")


def extract_facts(source: str, *, source_version: str) -> tuple[SemanticFact, ...]:
    if source_version == OLD_VERSION:
        candidate = False
    elif source_version == TARGET_VERSION:
        candidate = True
    else:
        _fail("AIDL-S008", f"unknown source version {source_version!r}")
    facts = [
        _fact(rule, match, source, candidate=candidate)
        for rule, match in _matches(source, candidate=candidate)
    ]
    return tuple(sorted(facts, key=lambda fact: (ROW_IDS.index(fact.row_id), fact.identity)))


def _replacement(rule: _Rule, match: re.Match[str]) -> str:
    g = match.groupdict()
    i = g.get("i") or ""
    tail = g.get("tail") or ""
    row = rule.row_id
    if row == "projection-relationship":
        sources = _clean_csv(g["sources"])
        if len(sources) != 1:
            _fail("AIDL-S004", "E5 bounded projection rewrite requires exactly one source", match.start())
        return f"{i}projection {g['name']} {{{tail}\n{i}  source: {sources[0]}\n{i}  target: {g['target']}"
    if row == "client-target":
        return f"{i}client {g['name']} {{{tail}\n{i}  service: {g['service']}"
    if row == "migration-source-target":
        return f"{i}migration {g['name']} {{{tail}\n{i}  from: {g['from']}\n{i}  to: {g['to']}"
    if row == "consumer-relationship":
        return f"{i}consumer {g['name']} {{{tail}\n{i}  topic: {g['topic']}\n{i}  source: {g['source']}"
    if row == "explicit-field-child":
        mods = (
            " " + " ".join((g.get("mods") or "").strip().split())
            if (g.get("mods") or "").strip()
            else ""
        )
        return f"{i}field {g['name']}: {g['type']}{mods}{tail}"
    if row == "explicit-index":
        fields = ", ".join(
            " ".join(part) if part[1] != "default" else part[0]
            for part in _index_fields(g["fields"])
        )
        return f"{i}index {g['name']}: ({fields}){tail}"
    if row == "queue-deadletter":
        return f"{i}deadLetter: {g['count']} attempts{tail}"
    if row == "schedule-lease":
        return f"{i}singleton: lease {g['duration']}{tail}"
    if row == "sync-outbox":
        return f"{i}changes: {g['target']} via outbox{tail}"
    raise AssertionError(row)


def _validate_old_source(source: str) -> None:
    _, diagnostics, _ = parse_text(source)
    if diagnostics:
        first = diagnostics[0]
        _fail(
            "AIDL-S005",
            f"legacy fixture is not accepted by production parser: {first.message}",
            first.start.offset,
        )


def _validate_sidecar(sidecar: LosslessSidecar, source: str, expected_schema: str) -> None:
    if sidecar.source != source or sidecar.source_fingerprint != source_fingerprint(source):
        _fail("AIDL-S008", "stale source fingerprint")
    if sidecar.schema_fingerprint != expected_schema:
        _fail("AIDL-S008", "stale schema fingerprint")
    ordered = sorted(sidecar.anchors, key=lambda a: (a.start, a.end, a.anchor_id))
    seen_ids: set[str] = set()
    previous_end = -1
    for anchor in ordered:
        if anchor.anchor_id in seen_ids:
            _fail("AIDL-S005", f"ambiguous anchor {anchor.anchor_id}", anchor.start)
        seen_ids.add(anchor.anchor_id)
        if anchor.start < previous_end:
            _fail("AIDL-S005", f"overlapping anchor {anchor.anchor_id}", anchor.start)
        previous_end = max(previous_end, anchor.end)


def _apply(source: str, edits: tuple[Edit, ...]) -> tuple[str, tuple[Relocation, ...]]:
    cursor = 0
    out: list[str] = []
    relocations: list[Relocation] = []
    new_cursor = 0
    for edit in sorted(edits, key=lambda e: (e.start, e.end)):
        if edit.start < cursor:
            _fail("AIDL-S005", f"overlapping edit {edit.anchor_id}", edit.start)
        untouched = source[cursor:edit.start]
        out.append(untouched)
        new_cursor += len(untouched)
        new_start = new_cursor
        out.append(edit.replacement)
        new_cursor += len(edit.replacement)
        relocations.append(
            Relocation(edit.anchor_id, edit.start, edit.end, new_start, new_cursor)
        )
        cursor = edit.end
    out.append(source[cursor:])
    return "".join(out), tuple(relocations)


def _candidate_is_valid(source: str) -> None:
    lingering = list(_matches(source, candidate=False))
    if lingering:
        rule, match = lingering[0]
        _fail("AIDL-S007", f"legacy spelling remains for {rule.row_id}", match.start())
    _ = extract_facts(source, source_version=TARGET_VERSION)


def _e3_replay(source: str, facts: tuple[SemanticFact, ...]) -> tuple[str, ...]:
    """Replay E3 construction where E3 can represent the exact bounded facts."""
    replayed: list[str] = []
    for fact in facts:
        values = dict(fact.facts)
        if fact.row_id == "projection-relationship":
            snippet = (
                f"projection {fact.identity} {{\n"
                f"  source: {values['sources'][0]}\n"
                f"  target: {values['target']}\n"
                "}\n"
            )
        elif fact.row_id == "client-target":
            snippet = f"client {fact.identity} {{\n  service: {values['service']}\n}}\n"
        elif fact.row_id == "migration-source-target":
            snippet = (
                f"migration {fact.identity} {{\n"
                f'  from: "{values["from"]}"\n'
                f'  to: "{values["to"]}"\n'
                "}\n"
            )
        elif fact.row_id == "consumer-relationship":
            snippet = (
                f"consumer {fact.identity} {{\n"
                f"  topic: {values['topic']}\n"
                f"  source: {values['source']}\n"
                "}\n"
            )
        elif fact.row_id == "explicit-field-child":
            if values["modifiers"]:
                continue
            snippet = f"entity E5Replay {{\n  field {fact.identity}: {values['type']}\n}}\n"
        else:
            continue
        parse_e3_candidate(snippet, source_version=E3_VERSION, schema_version=E3_VERSION)
        replayed.append(fact.row_id)
    return tuple(replayed)


def format_candidate(
    source: str,
    *,
    source_version: str,
    schema_fingerprint: str,
) -> str:
    if source_version != TARGET_VERSION or schema_fingerprint != TARGET_SCHEMA_FINGERPRINT:
        _fail("AIDL-S008", "Formatter(v) requires exact selected candidate schema")
    if list(_matches(source, candidate=False)):
        _fail("AIDL-S007", "Formatter(target) does not accept legacy spelling")
    edits: list[Edit] = []
    sidecar = build_sidecar(
        source,
        source_version=TARGET_VERSION,
        schema_fingerprint=schema_fingerprint,
    )
    by_id = {a.anchor_id: a for a in sidecar.anchors}
    counts: dict[str, int] = {}
    for rule, match in _matches(source, candidate=True):
        index = counts.get(rule.row_id, 0)
        counts[rule.row_id] = index + 1
        anchor_id = f"{rule.row_id}:{index}"
        anchor = by_id.get(anchor_id)
        if anchor is None:
            _fail("AIDL-S005", f"missing candidate anchor {anchor_id}", match.start())
        g = match.groupdict()
        i = g.get("i") or ""
        tail = g.get("tail") or ""
        if rule.row_id == "projection-relationship":
            replacement = f"{i}projection {g['name']} {{{tail}\n{i}  source: {g['source']}\n{i}  target: {g['target']}"
        elif rule.row_id == "client-target":
            replacement = f"{i}client {g['name']} {{{tail}\n{i}  service: {g['service']}"
        elif rule.row_id == "migration-source-target":
            replacement = f"{i}migration {g['name']} {{{tail}\n{i}  from: {g['from']}\n{i}  to: {g['to']}"
        elif rule.row_id == "consumer-relationship":
            replacement = f"{i}consumer {g['name']} {{{tail}\n{i}  topic: {g['topic']}\n{i}  source: {g['source']}"
        elif rule.row_id == "explicit-field-child":
            mods = (
                " " + " ".join((g.get("mods") or "").strip().split())
                if (g.get("mods") or "").strip()
                else ""
            )
            replacement = f"{i}field {g['name']}: {g['type']}{mods}{tail}"
        elif rule.row_id == "explicit-index":
            fields = ", ".join(
                " ".join(p) if p[1] != "default" else p[0]
                for p in _index_fields(g["fields"])
            )
            replacement = f"{i}index {g['name']}: ({fields}){tail}"
        elif rule.row_id == "queue-deadletter":
            replacement = f"{i}deadLetter: {g['count']} attempts{tail}"
        elif rule.row_id == "schedule-lease":
            replacement = f"{i}singleton: lease {g['duration']}{tail}"
        elif rule.row_id == "sync-outbox":
            replacement = f"{i}changes: {g['target']} via outbox{tail}"
        else:
            raise AssertionError(rule.row_id)
        if replacement != match.group(0):
            edits.append(
                Edit(anchor_id, rule.row_id, match.start(), match.end(), replacement)
            )
    formatted, _ = _apply(source, tuple(edits))
    return formatted


def plan_migration(
    source: str,
    *,
    source_version: str,
    old_version: str,
    target_version: str,
    source_schema_fingerprint: str,
    target_schema_fingerprint: str,
    expected_source_fingerprint: str,
    sidecar: LosslessSidecar | None = None,
) -> MigrationPlan:
    if old_version != OLD_VERSION or target_version != TARGET_VERSION:
        _fail("AIDL-S008", "unknown or stale migration version pair")
    if target_schema_fingerprint != TARGET_SCHEMA_FINGERPRINT:
        _fail("AIDL-S008", "unknown or stale target schema fingerprint")
    if expected_source_fingerprint != source_fingerprint(source):
        _fail("AIDL-S008", "stale source fingerprint")
    if source_version == TARGET_VERSION:
        if source_schema_fingerprint != TARGET_SCHEMA_FINGERPRINT:
            _fail("AIDL-S008", "target source/schema fingerprint mismatch")
        sidecar = sidecar or build_sidecar(
            source,
            source_version=TARGET_VERSION,
            schema_fingerprint=source_schema_fingerprint,
        )
        _validate_sidecar(sidecar, source, TARGET_SCHEMA_FINGERPRINT)
        _candidate_is_valid(source)
        facts = extract_facts(source, source_version=TARGET_VERSION)
        replayed = _e3_replay(source, facts)
        return MigrationPlan(
            source_version,
            old_version,
            target_version,
            OLD_SCHEMA_FINGERPRINT,
            TARGET_SCHEMA_FINGERPRINT,
            source_fingerprint(source),
            (),
            (),
            "compatible",
            facts,
            facts,
            source,
            replayed,
        )
    if source_version != OLD_VERSION or source_schema_fingerprint != OLD_SCHEMA_FINGERPRINT:
        _fail("AIDL-S008", "old source/schema fingerprint mismatch")

    _validate_old_source(source)
    sidecar = sidecar or build_sidecar(
        source,
        source_version=OLD_VERSION,
        schema_fingerprint=source_schema_fingerprint,
    )
    _validate_sidecar(sidecar, source, OLD_SCHEMA_FINGERPRINT)
    anchors = {a.anchor_id: a for a in sidecar.anchors}

    edits: list[Edit] = []
    counts: dict[str, int] = {}
    old_matches = list(_matches(source, candidate=False))
    for rule, match in old_matches:
        index = counts.get(rule.row_id, 0)
        counts[rule.row_id] = index + 1
        anchor_id = f"{rule.row_id}:{index}"
        anchor = anchors.get(anchor_id)
        if anchor is None or (anchor.start, anchor.end) != (match.start(), match.end()):
            _fail("AIDL-S005", f"missing or stale anchor {anchor_id}", match.start())
        edits.append(
            Edit(
                anchor_id,
                rule.row_id,
                match.start(),
                match.end(),
                _replacement(rule, match),
            )
        )

    migrated, relocations = _apply(source, tuple(edits))
    formatted = format_candidate(
        migrated,
        source_version=TARGET_VERSION,
        schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,
    )
    _candidate_is_valid(formatted)

    old_facts = extract_facts(source, source_version=OLD_VERSION)
    target_facts = extract_facts(formatted, source_version=TARGET_VERSION)
    if old_facts != target_facts:
        _fail("AIDL-S004", "bounded semantic fact comparison is not compatible")
    replayed = _e3_replay(formatted, target_facts)

    if formatted != migrated:
        _fail("AIDL-S005", "migrator emitted non-canonical target source")

    return MigrationPlan(
        source_version,
        old_version,
        target_version,
        OLD_SCHEMA_FINGERPRINT,
        TARGET_SCHEMA_FINGERPRINT,
        source_fingerprint(source),
        tuple(edits),
        relocations,
        "compatible",
        old_facts,
        target_facts,
        source,
        replayed,
    )


def apply_plan(source: str, plan: MigrationPlan) -> MigrationResult:
    if plan.source_fingerprint != source_fingerprint(source):
        _fail("AIDL-S008", "stale source fingerprint at apply")
    migrated, relocations = _apply(source, plan.edits)
    if relocations != plan.relocations:
        _fail("AIDL-S005", "non-deterministic relocation metadata")
    if extract_facts(migrated, source_version=TARGET_VERSION) != plan.target_facts:
        _fail("AIDL-S004", "semantic facts changed while applying plan")
    return MigrationResult(migrated, plan)


def migrate(source: str, **kwargs: Any) -> MigrationResult:
    plan = plan_migration(source, **kwargs)
    return apply_plan(source, plan) if plan.edits else MigrationResult(source, plan)


def with_anchors(sidecar: LosslessSidecar, anchors: Iterable[Anchor]) -> LosslessSidecar:
    """Test/prototype hook for exercising fail-closed anchor conditions."""
    return replace(sidecar, anchors=tuple(anchors))
