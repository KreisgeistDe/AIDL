#!/usr/bin/env python3
"""Static consistency checks for the AIDL reference specification.

This is deliberately not a parser or compiler. It catches specification drift,
unsafe example patterns, unresolved example imports and missing conformance
contracts before the reference compiler exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DECLARATION_KINDS = (
    "native function",
    "native component",
    "syncStatus",
    "app",
    "auth",
    "a11y",
    "privacy",
    "enum",
    "alias",
    "opaque",
    "value",
    "union",
    "error",
    "entity",
    "view",
    "api",
    "policy",
    "query",
    "mutation",
    "event",
    "topic",
    "queue",
    "consumer",
    "projection",
    "workflow",
    "saga",
    "task",
    "schedule",
    "system",
    "service",
    "client",
    "tenant",
    "channel",
    "resource",
    "media",
    "rendition",
    "sync",
    "migration",
    "deployment",
    "frontend",
    "theme",
    "component",
    "page",
    "form",
    "action",
    "seo",
    "fixture",
    "test",
    "scenario",
)

BLOCK_KINDS = {
    "entity",
    "mutation",
    "event",
    "topic",
    "consumer",
    "projection",
    "workflow",
    "task",
    "channel",
    "sync",
    "service",
    "system",
}

REQUIRED_DOCS = {
    "00-overview.md",
    "01-core-language.md",
    "02-backend.md",
    "03-frontend.md",
    "04-agent-tooling.md",
    "05-diagnostics-testing.md",
    "06-grammar.md",
    "07-distributed-systems.md",
    "08-offline-sync.md",
    "09-resources-deployment.md",
    "10-evolution-compatibility.md",
    "11-standard-library.md",
    "12-coverage-and-limits.md",
    "13-ir-adapter-contract.md",
}


UNRESOLVED_PLACEHOLDER = re.compile(r"\b(?:TBD|FIXME)\b|\bTODO\b(?!\.md\b)")


@dataclass(frozen=True)
class Block:
    kind: str
    name: str
    body: str
    path: Path
    start: int


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks = 0

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.warnings.append(message)


def mask_strings_and_comments(text: str) -> str:
    """Replace strings/comments with spaces while preserving offsets/newlines."""

    chars = list(text)
    i = 0
    state = "code"
    while i < len(chars):
        ch = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if state == "code":
            if ch == '"':
                chars[i] = " "
                state = "string"
            elif ch == "/" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                i += 1
                state = "line_comment"
            elif ch == "/" and nxt == "*":
                chars[i] = chars[i + 1] = " "
                i += 1
                state = "block_comment"
        elif state == "string":
            if ch == "\\":
                chars[i] = " "
                if i + 1 < len(chars):
                    i += 1
                    chars[i] = " "
            elif ch == '"':
                chars[i] = " "
                state = "code"
            elif ch != "\n":
                chars[i] = " "
        elif state == "line_comment":
            if ch == "\n":
                state = "code"
            else:
                chars[i] = " "
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                i += 1
                state = "code"
            elif ch != "\n":
                chars[i] = " "
        i += 1
    return "".join(chars)


def matching_brace(masked: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def named_blocks(path: Path, text: str, kind: str) -> list[Block]:
    masked = mask_strings_and_comments(text)
    if kind == "consumer":
        pattern = re.compile(
            r"(?m)^(?:export\s+)?consumer\s+([A-Z][A-Za-z0-9_]*)\s+"
            r"on\s+[A-Z][A-Za-z0-9_.]*\s+from\s+[A-Z][A-Za-z0-9_.]*\s*\{"
        )
    elif kind == "sync":
        pattern = re.compile(
            r"(?m)^(?:export\s+)?sync\s+([A-Z][A-Za-z0-9_]*)\s+"
            r"for\s+[A-Z][A-Za-z0-9_.<>?]*\s*\{"
        )
    else:
        pattern = re.compile(
            rf"(?m)^(?:export\s+)?{re.escape(kind)}\s+"
            rf"([A-Za-z][A-Za-z0-9_]*)"
            rf"(?:\s*<[^{{}}]*>)?(?:\s*\([^{{}}]*\))?"
            rf"(?:\s+from\s+[A-Z][A-Za-z0-9_.<>?]*)?"
            rf"(?:\s+version\s+\d+)?[^{{}}]*\{{"
        )
    result: list[Block] = []
    for match in pattern.finditer(masked):
        opening = masked.find("{", match.start(), match.end())
        closing = matching_brace(masked, opening)
        if closing is not None:
            result.append(
                Block(
                    kind=kind,
                    name=match.group(1),
                    body=text[opening + 1 : closing],
                    path=path,
                    start=match.start(),
                )
            )
    return result


def declaration_names(text: str) -> set[str]:
    names: set[str] = set()
    patterns = [
        r"(?m)^(?:export\s+)?(?:app|enum|alias|opaque|value|union|error|"
        r"entity|view|api|policy|query|mutation|event|topic|queue|consumer|"
        r"projection|workflow|saga|task|schedule|system|service|client|"
        r"channel|resource|media|rendition|sync|migration|frontend|theme|"
        r"component|page|form|syncStatus)\s+([A-Za-z][A-Za-z0-9_]*)",
        r"(?m)^(?:export\s+)?action\s+([a-z][A-Za-z0-9_]*)",
        r"(?m)^(?:export\s+)?native\s+function\s+([A-Za-z][A-Za-z0-9_.]*)",
        r"(?m)^(?:export\s+)?native\s+component\s+([A-Z][A-Za-z0-9_]*)",
    ]
    for pattern in patterns:
        names.update(re.findall(pattern, text))
    return names


def split_names(value: str) -> list[str]:
    return [
        token.strip().split()[-1]
        for token in value.replace("\n", " ").split(",")
        if token.strip()
    ]


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_balanced(path: Path, text: str, report: Report) -> None:
    masked = mask_strings_and_comments(text)
    pairs = {"{": "}", "[": "]", "(": ")"}
    closers = {value: key for key, value in pairs.items()}
    stack: list[tuple[str, int]] = []
    for index, char in enumerate(masked):
        if char in pairs:
            stack.append((char, index))
        elif char in closers:
            if not stack or stack[-1][0] != closers[char]:
                report.errors.append(
                    f"{path}:{line_number(text, index)}: unmatched {char}"
                )
                return
            stack.pop()
    for char, index in stack:
        report.errors.append(
            f"{path}:{line_number(text, index)}: unclosed {char}"
        )


def check_imports(
    files: dict[Path, str],
    module_files: dict[str, Path],
    module_symbols: dict[str, set[str]],
    report: Report,
) -> None:
    modules_by_length = sorted(module_files, key=len, reverse=True)
    module_for_path = {path: module for module, path in module_files.items()}
    graph: dict[str, set[str]] = {module: set() for module in module_files}
    for path, text in files.items():
        for imported in re.findall(r"(?m)^import\s+([A-Za-z0-9_.*-]+)\s*$", text):
            if imported.startswith("aidl."):
                continue
            target = imported[:-2] if imported.endswith(".*") else imported
            module = next(
                (
                    candidate
                    for candidate in modules_by_length
                    if target == candidate or target.startswith(candidate + ".")
                ),
                None,
            )
            report.check(
                module is not None,
                f"{path}: unresolved import {imported}",
            )
            if module is None or target == module or imported.endswith(".*"):
                if module is not None:
                    graph[module_for_path[path]].add(module)
                continue
            graph[module_for_path[path]].add(module)
            symbol = target[len(module) + 1 :]
            report.check(
                symbol in module_symbols[module],
                f"{path}: import {imported} references unknown symbol {symbol}",
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module: str, trail: list[str]) -> None:
        if module in visiting:
            start = trail.index(module)
            report.errors.append(
                "cyclic module imports: " + " -> ".join(trail[start:] + [module])
            )
            return
        if module in visited:
            return
        visiting.add(module)
        for dependency in sorted(graph[module]):
            visit(dependency, trail + [dependency])
        visiting.remove(module)
        visited.add(module)

    for module in sorted(graph):
        visit(module, [module])


def check_aidl_files(root: Path, files: dict[Path, str], report: Report) -> None:
    modules: dict[str, Path] = {}
    module_symbols: dict[str, set[str]] = {}

    for path, text in files.items():
        report.check("\t" not in text, f"{path}: tabs are forbidden")
        masked = mask_strings_and_comments(text)
        report.check(";" not in masked, f"{path}: semicolons are forbidden")
        check_balanced(path, text, report)

        module_matches = re.findall(
            r"(?m)^module\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*$", text
        )
        report.check(
            len(module_matches) == 1,
            f"{path}: expected exactly one module declaration",
        )
        if len(module_matches) == 1:
            module = module_matches[0]
            report.check(
                module not in modules,
                f"{path}: duplicate module {module}; first seen in {modules.get(module)}",
            )
            modules[module] = path
            module_symbols[module] = declaration_names(text)

    check_imports(files, modules, module_symbols, report)

    grammar = (root / "docs" / "06-grammar.md").read_text(encoding="utf-8")
    used_kinds: set[str] = set()
    declaration_pattern = "|".join(
        re.escape(kind) for kind in sorted(DECLARATION_KINDS, key=len, reverse=True)
    )
    for text in files.values():
        used_kinds.update(
            re.findall(
                rf"(?m)^(?:export\s+)?({declaration_pattern})\b",
                mask_strings_and_comments(text),
            )
        )
    for kind in sorted(used_kinds):
        tokens = kind.split()
        report.check(
            all(f'"{token}"' in grammar for token in tokens),
            f"grammar does not declare example declaration kind {kind}",
        )


def check_project(project: Path, report: Report) -> None:
    files = {
        path: path.read_text(encoding="utf-8")
        for path in sorted(project.rglob("*.aidl"))
    }
    report.check(bool(files), f"{project}: no AIDL files")

    all_blocks: dict[str, list[Block]] = defaultdict(list)
    for path, text in files.items():
        for kind in BLOCK_KINDS:
            all_blocks[kind].extend(named_blocks(path, text, kind))

    entities = {block.name: block for block in all_blocks["entity"]}
    owners: dict[str, list[str]] = defaultdict(list)
    service_uses: dict[str, list[str]] = {}
    service_dependencies: dict[str, set[str]] = {}
    service_reliability: dict[str, set[str]] = {}
    declaration_owner: dict[str, str] = {}
    all_declarations: set[str] = set()
    declaration_kind: dict[str, str] = {}
    for text in files.values():
        for kind in (
            "query",
            "mutation",
            "api",
            "consumer",
            "workflow",
            "task",
            "schedule",
            "projection",
            "sync",
            "channel",
            "resource",
            "topic",
            "queue",
            "entity",
            "service",
            "system",
        ):
            for name in re.findall(
                rf"(?m)^(?:export\s+)?{kind}\s+([A-Za-z][A-Za-z0-9_]*)",
                text,
            ):
                all_declarations.add(name)
                declaration_kind[name] = kind

    for service in all_blocks["service"]:
        owns_match = re.search(r"\bowns\s*\[([^\]]*)\]", service.body, re.S)
        if owns_match:
            for entity in split_names(owns_match.group(1)):
                owners[entity].append(service.name)
        uses_match = re.search(r"\buses\s*\[([^\]]*)\]", service.body, re.S)
        if uses_match:
            service_uses[service.name] = split_names(uses_match.group(1))
            for resource in service_uses[service.name]:
                report.check(
                    resource in all_declarations,
                    f"{service.path}: service {service.name} uses unknown "
                    f"resource {resource}",
                )
        exposes_match = re.search(
            r"\bexposes\s*\[([^\]]*)\]", service.body, re.S
        )
        if exposes_match:
            for exposed in split_names(exposes_match.group(1)):
                report.check(
                    exposed in all_declarations,
                    f"{service.path}: service {service.name} exposes unknown "
                    f"declaration {exposed}",
                )
                declaration_owner[exposed] = service.name
        runs_match = re.search(r"\bruns\s*\[([^\]]*)\]", service.body, re.S)
        if runs_match:
            for runnable in split_names(runs_match.group(1)):
                report.check(
                    runnable in all_declarations,
                    f"{service.path}: service {service.name} runs unknown "
                    f"declaration {runnable}",
                )
                declaration_owner[runnable] = service.name
        depends_match = re.search(
            r"\bdependsOn\s*\[([^\]]*)\]", service.body, re.S
        )
        service_dependencies[service.name] = (
            set(split_names(depends_match.group(1))) if depends_match else set()
        )
        reliability_match = re.search(
            r"\breliability\s*\{([^{}]*)\}", service.body, re.S
        )
        service_reliability[service.name] = (
            set(
                re.findall(
                    r"(?m)^\s*([a-z][A-Za-z0-9_]*)\s+", 
                    reliability_match.group(1),
                )
            )
            if reliability_match
            else set()
        )

    for system in all_blocks["system"]:
        service_list = re.search(
            r"\bservices\s*\[([^\]]*)\]", system.body, re.S
        )
        resource_list = re.search(
            r"\bresources\s*\[([^\]]*)\]", system.body, re.S
        )
        api_list = re.search(r"\bapis\s*\[([^\]]*)\]", system.body, re.S)
        report.check(
            service_list is not None,
            f"{system.path}: system {system.name} has no services list",
        )
        report.check(
            resource_list is not None,
            f"{system.path}: system {system.name} has no resources list",
        )
        if service_list:
            for service_name in split_names(service_list.group(1)):
                report.check(
                    declaration_kind.get(service_name) == "service",
                    f"{system.path}: system {system.name} references unknown "
                    f"service {service_name}",
                )
        if resource_list:
            for resource_name in split_names(resource_list.group(1)):
                report.check(
                    declaration_kind.get(resource_name)
                    in {"resource", "topic", "queue"},
                    f"{system.path}: system {system.name} references unknown "
                    f"resource {resource_name}",
                )
        if api_list:
            for api_name in split_names(api_list.group(1)):
                report.check(
                    declaration_kind.get(api_name) == "api",
                    f"{system.path}: system {system.name} references unknown "
                    f"api {api_name}",
                )

    for path, text in files.items():
        for api in named_blocks(path, text, "api"):
            operations = re.search(
                r"\boperations\s*\[([^\]]*)\]", api.body, re.S
            )
            report.check(
                operations is not None,
                f"{api.path}: api {api.name} has no operations list",
            )
            if operations:
                for operation in split_names(operations.group(1)):
                    report.check(
                        operation in all_declarations,
                        f"{api.path}: api {api.name} exposes unknown "
                        f"operation {operation}",
                    )
            for clause in ("transport", "version", "compatibility", "rateLimit"):
                report.check(
                    bool(re.search(rf"\b{clause}\b", api.body)),
                    f"{api.path}: api {api.name} misses {clause}",
                )

    for entity in entities:
        report.check(
            len(owners.get(entity, [])) == 1,
            f"{project.name}: entity {entity} must have exactly one service owner; "
            f"found {owners.get(entity, [])}",
        )

    for entity in all_blocks["entity"]:
        if re.search(r"\bmutable\b", entity.body):
            report.check(
                bool(
                    re.search(
                        r"(?m)^\s*\w+\s*:\s*revision\b[^\n]*"
                        r"\bconcurrencyToken\b",
                        entity.body,
                    )
                ),
                f"{entity.path}: mutable entity {entity.name} has no revision "
                "concurrencyToken",
            )
        for target in re.findall(
            r"(?m)^\s*\w+\s*:\s*ref\s+([A-Z][A-Za-z0-9_]*)\b",
            entity.body,
        ):
            if target not in entities:
                report.errors.append(
                    f"{entity.path}: ref target {target} is not an entity in project"
                )
                continue
            report.check(
                owners.get(entity.name) == owners.get(target),
                f"{entity.path}: cross-owner ref {entity.name} -> {target}",
            )

    for mutation in all_blocks["mutation"]:
        for clause in ("auth:", "allow:", "errors:", "idempotency:"):
            report.check(
                clause in mutation.body,
                f"{mutation.path}: mutation {mutation.name} misses {clause}",
            )
        root_effects = int("transaction on" in mutation.body) + int(
            bool(re.search(r"(?m)^\s{2}call\s*:", mutation.body))
        )
        report.check(
            root_effects == 1,
            f"{mutation.path}: mutation {mutation.name} must have exactly one "
            "transaction or direct call root effect",
        )
        for emit in re.finditer(r"\bemit\s*:", mutation.body):
            tail = mutation.body[emit.start() : emit.start() + 1000]
            report.check(
                bool(re.search(r"\bvia\s+outbox\b", tail)),
                f"{mutation.path}: mutation {mutation.name} emits without outbox",
            )
        for target in re.findall(
            r"\bauthorize\s*:\s*remote\s+query\s+([a-z][A-Za-z0-9_]*)",
            mutation.body,
        ):
            source_service = declaration_owner.get(mutation.name)
            target_service = declaration_owner.get(target)
            report.check(
                source_service is not None and target_service is not None,
                f"{mutation.path}: cannot resolve service edge for remote "
                f"authorization {mutation.name} -> {target}",
            )
            if source_service and target_service:
                report.check(
                    target_service in service_dependencies.get(
                        source_service, set()
                    ),
                    f"{mutation.path}: {source_service} remotely calls "
                    f"{target_service} without dependsOn",
                )
                report.check(
                    source_service != target_service,
                    f"{mutation.path}: remote query {target} resolves to the "
                    f"same service {source_service}",
                )

    reliability_requirements = {
        "mutation": "idempotencyStore",
        "consumer": "inboxStore",
        "workflow": "workflowStore",
        "projection": "projectionStore",
        "sync": "syncStore",
    }
    for kind, required_store in reliability_requirements.items():
        for block in all_blocks[kind]:
            service_name = declaration_owner.get(block.name)
            report.check(
                service_name is not None,
                f"{block.path}: {kind} {block.name} has no service owner",
            )
            if service_name:
                report.check(
                    required_store
                    in service_reliability.get(service_name, set()),
                    f"{block.path}: service {service_name} runs {kind} "
                    f"{block.name} without {required_store}",
                )

    for event in all_blocks["event"]:
        report.check(
            bool(
                re.search(
                    r"(?m)^\s*eventId\s*:\s*OperationId\b", event.body
                )
            ),
            f"{event.path}: event {event.name} needs eventId: OperationId",
        )
        report.check(
            bool(re.search(r"(?m)^\s*occurredAt\s*:", event.body)),
            f"{event.path}: event {event.name} has no occurredAt",
        )

    topic_events: dict[str, set[str]] = {}
    for topic in all_blocks["topic"]:
        required = (
            "delivery",
            "ordering",
            "retention",
            "compatibility",
            "deadLetter",
        )
        for clause in required:
            report.check(
                bool(re.search(rf"\b{clause}\b", topic.body)),
                f"{topic.path}: topic {topic.name} misses {clause}",
            )
        events = re.search(r"\bevents\s*\[([^\]]*)\]", topic.body, re.S)
        topic_events[topic.name] = (
            set(split_names(events.group(1))) if events else set()
        )

    for consumer in all_blocks["consumer"]:
        report.check(
            "idempotency:" in consumer.body,
            f"{consumer.path}: consumer {consumer.name} has no idempotency",
        )
        header_source = files[consumer.path][consumer.start : consumer.start + 300]
        match = re.search(
            r"consumer\s+\w+\s+on\s+([A-Z]\w*)\s+from\s+([A-Z]\w*)",
            header_source,
        )
        if match:
            event_name, topic_name = match.groups()
            report.check(
                event_name in topic_events.get(topic_name, set()),
                f"{consumer.path}: consumer {consumer.name} reads {event_name} "
                f"from topic {topic_name}, but the topic does not carry it",
            )

    for sync in all_blocks["sync"]:
        if re.search(r"\bmode\s+replicated\b", sync.body):
            for clause in ("operationLog", "delete tombstone", "conflict"):
                report.check(
                    clause in sync.body,
                    f"{sync.path}: replicated sync {sync.name} misses {clause}",
                )
            report.check(
                not bool(
                    re.search(
                        r"\blww\s*\(\s*clock\s*:\s*(deviceTime|clientTime)",
                        sync.body,
                    )
                ),
                f"{sync.path}: sync {sync.name} uses an unsafe client clock",
            )

    for lock in project.rglob("aidl.lock"):
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.errors.append(f"{lock}: invalid JSON: {exc}")
            continue
        report.check("core" in data.get("profiles", {}), f"{lock}: core profile absent")
        report.check(
            data.get("standardLibrary") == "aidl.std",
            f"{lock}: standard library identity must be aidl.std",
        )
        grammar_bytes = (
            project.parent.parent / "docs" / "06-grammar.md"
        ).read_bytes()
        grammar_hash = "sha256:" + hashlib.sha256(grammar_bytes).hexdigest()
        report.check(
            data.get("grammar") == grammar_hash,
            f"{lock}: grammar hash is stale; expected {grammar_hash}",
        )

        app_profiles: dict[str, int] = {}
        for text in files.values():
            for profile, major in re.findall(
                r"(?m)^\s*profile\s+([a-z][a-z0-9-]*)\s+version\s+(\d+)\s*$",
                text,
            ):
                app_profiles[profile] = int(major)
        report.check(
            data.get("profiles") == app_profiles,
            f"{lock}: locked profiles do not match app profiles "
            f"{app_profiles}",
        )

    report.check(
        any(re.search(r"\bprofile\s+core\s+version\s+1\b", text) for text in files.values()),
        f"{project}: app does not activate core profile version 1",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = Report()

    report.check((root / "README.md").is_file(), "README.md is missing")
    report.check((root / "CHANGELOG.md").is_file(), "CHANGELOG.md is missing")
    docs = root / "docs"
    existing_docs = {path.name for path in docs.glob("*.md")}
    for required in sorted(REQUIRED_DOCS):
        report.check(required in existing_docs, f"docs/{required} is missing")
    for markdown in sorted(root.rglob("*.md")):
        text = markdown.read_text(encoding="utf-8")
        report.check(
            text.count("~~~") % 2 == 0,
            f"{markdown}: unbalanced Markdown code fence",
        )
        report.check("\t" not in text, f"{markdown}: tabs are forbidden")
        report.check(
            not bool(UNRESOLVED_PLACEHOLDER.search(text)),
            f"{markdown}: unresolved placeholder",
        )

    for spec_name in ("ir.schema.json", "profile-registry.json"):
        spec_path = root / "spec" / spec_name
        report.check(spec_path.is_file(), f"spec/{spec_name} is missing")
        if spec_path.is_file():
            try:
                spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                report.errors.append(f"{spec_path}: invalid JSON: {exc}")
            else:
                report.check(
                    spec_data.get("$schema")
                    == "https://json-schema.org/draft/2020-12/schema",
                    f"{spec_path}: must target JSON Schema 2020-12",
                )

    aidl_files = {
        path: path.read_text(encoding="utf-8")
        for path in sorted((root / "examples").rglob("*.aidl"))
    }
    check_aidl_files(root, aidl_files, report)

    projects = [
        path
        for path in sorted((root / "examples").iterdir())
        if path.is_dir()
    ]
    report.check(
        {path.name for path in projects}
        >= {"petstore", "calendar-offline", "videohub"},
        "three required reference projects are not present",
    )
    for project in projects:
        check_project(project, report)

    result = {
        "status": "passed" if not report.errors else "failed",
        "checks": report.checks,
        "aidlFiles": len(aidl_files),
        "projects": len(projects),
        "errors": report.errors,
        "warnings": report.warnings,
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            f"AIDL spec lint: {result['status'].upper()} "
            f"({report.checks} checks, {len(aidl_files)} AIDL files, "
            f"{len(projects)} projects)"
        )
        for error in report.errors:
            print(f"ERROR: {error}")
        for warning in report.warnings:
            print(f"WARNING: {warning}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
