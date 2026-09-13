from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from tools.core_bootstrap import BodyEntry, Declaration, TypeRef, Value, parse_source


BUILTIN_TYPES = {
    "bool", "bytes", "date", "datetime", "decimal", "duration", "email",
    "float", "int", "json", "long", "revision", "string", "time", "url", "uuid",
}


@dataclass(frozen=True)
class Cardinality:
    minimum: int
    maximum: int | None

    def accepts(self, count: int) -> bool:
        return count >= self.minimum and (self.maximum is None or count <= self.maximum)

    def describe(self) -> str:
        maximum = "unbounded" if self.maximum is None else str(self.maximum)
        return f"occurrence {self.minimum}..{maximum}"


@dataclass(frozen=True)
class ArgumentContract:
    name: str
    type_ref: TypeRef
    cardinality: Cardinality


@dataclass(frozen=True)
class ModifierContract:
    name: str
    targets: tuple[str, ...]
    arguments: tuple[ArgumentContract, ...]
    cardinality: Cardinality


@dataclass(frozen=True)
class BodySlotContract:
    body_type: str
    name_policy: str
    value_type: TypeRef | None
    cardinality: Cardinality
    ordered: bool
    unique_by_name: bool
    modifiers: tuple[str, ...]


@dataclass(frozen=True)
class DeclarationContract:
    kind: str
    name_policy: str
    arguments: tuple[ArgumentContract, ...]
    result: TypeRef | None
    slots: tuple[BodySlotContract, ...]
    modifiers: tuple[str, ...]


@dataclass(frozen=True)
class MetaCombinator:
    name: str
    behavior: str
    arguments: Cardinality


@dataclass(frozen=True)
class SemanticRegistry:
    declarations: dict[str, DeclarationContract]
    modifiers: dict[str, ModifierContract]
    combinators: dict[str, MetaCombinator]


@dataclass(frozen=True)
class SemanticDiagnostic:
    code: str
    line: int
    column: int
    message: str
    expected: str

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "span": {"line": self.line, "column": self.column},
            "message": self.message,
            "expected": self.expected,
        }


class CoreContractError(ValueError):
    pass


def registry_digest(registry: SemanticRegistry) -> str:
    payload = {
        "declarations": {
            key: _contract_json(value) for key, value in sorted(registry.declarations.items())
        },
        "modifiers": {
            key: _modifier_json(value) for key, value in sorted(registry.modifiers.items())
        },
        "combinators": {
            key: {
                "behavior": value.behavior,
                "arguments": [value.arguments.minimum, value.arguments.maximum],
            }
            for key, value in sorted(registry.combinators.items())
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _type_json(type_ref: TypeRef | None) -> Any:
    return None if type_ref is None else type_ref.to_json()


def _argument_json(argument: ArgumentContract) -> dict[str, Any]:
    return {
        "name": argument.name,
        "type": _type_json(argument.type_ref),
        "cardinality": [argument.cardinality.minimum, argument.cardinality.maximum],
    }


def _modifier_json(modifier: ModifierContract) -> dict[str, Any]:
    return {
        "targets": list(modifier.targets),
        "arguments": [_argument_json(item) for item in modifier.arguments],
        "cardinality": [modifier.cardinality.minimum, modifier.cardinality.maximum],
    }


def _contract_json(contract: DeclarationContract) -> dict[str, Any]:
    return {
        "namePolicy": contract.name_policy,
        "arguments": [_argument_json(item) for item in contract.arguments],
        "result": _type_json(contract.result),
        "slots": [
            {
                "bodyType": slot.body_type,
                "namePolicy": slot.name_policy,
                "valueType": _type_json(slot.value_type),
                "cardinality": [slot.cardinality.minimum, slot.cardinality.maximum],
                "ordered": slot.ordered,
                "uniqueByName": slot.unique_by_name,
                "modifiers": list(slot.modifiers),
            }
            for slot in contract.slots
        ],
        "modifiers": list(contract.modifiers),
    }


class _SourceSpans:
    def __init__(self, source: str) -> None:
        self.lines = source.splitlines()

    def declaration(self, declaration: Declaration, start: int = 0) -> tuple[int, int]:
        pattern = re.compile(r"^\s*(?:export\s+)?" + re.escape(declaration.kind) + r"\b")
        for index in range(start, len(self.lines)):
            if pattern.search(self.lines[index]):
                return index + 1, len(self.lines[index]) - len(self.lines[index].lstrip()) + 1
        return 1, 1

    def body(self, entry: BodyEntry, start_line: int) -> tuple[int, int]:
        head = entry.body_type + ((" " + entry.name) if entry.name is not None else "")
        pattern = re.compile(r"^\s*" + re.escape(head) + r"\s*:")
        for index in range(max(0, start_line - 1), len(self.lines)):
            if pattern.search(self.lines[index]):
                return index + 1, len(self.lines[index]) - len(self.lines[index].lstrip()) + 1
        return start_line, 1


def _fmt_type(type_ref: TypeRef) -> str:
    suffix = "?" if type_ref.optional else ""
    if not type_ref.arguments:
        return type_ref.name + suffix
    return f"{type_ref.name}<" + ", ".join(_fmt_type(item) for item in type_ref.arguments) + ">" + suffix


def _check_name_policy(
    diagnostics: list[SemanticDiagnostic],
    policy: str,
    name: str | None,
    line: int,
    column: int,
    subject: str,
) -> None:
    if policy == "required" and name is None:
        diagnostics.append(SemanticDiagnostic("CORE-S001", line, column, f"{subject} requires an identifier", "NamePolicy required"))
    elif policy == "forbidden" and name is not None:
        diagnostics.append(SemanticDiagnostic("CORE-S002", line, column, f"{subject} forbids identifier {name!r}", "NamePolicy forbidden"))


def _count_named(items: Iterable[tuple[str, Value]]) -> dict[str, list[Value]]:
    result: dict[str, list[Value]] = {}
    for name, value in items:
        result.setdefault(name, []).append(value)
    return result


def _validate_arguments(
    diagnostics: list[SemanticDiagnostic],
    actual: tuple[tuple[str, Value], ...],
    contracts: tuple[ArgumentContract, ...],
    registry: SemanticRegistry,
    symbols: dict[str, Declaration],
    env: dict[str, TypeRef],
    line: int,
    column: int,
    subject: str,
) -> None:
    grouped = _count_named(actual)
    by_name = {item.name: item for item in contracts}
    for name in grouped:
        if name not in by_name:
            diagnostics.append(SemanticDiagnostic("CORE-S003", line, column, f"unknown named argument {name!r} on {subject}", "declared named arguments only"))
    for contract in contracts:
        values = grouped.get(contract.name, [])
        if not contract.cardinality.accepts(len(values)):
            diagnostics.append(SemanticDiagnostic("CORE-S004", line, column, f"argument {contract.name!r} occurs {len(values)} time(s) on {subject}", contract.cardinality.describe()))
        for value in values:
            _validate_value(diagnostics, value, contract.type_ref, registry, symbols, env, line, column, f"argument {contract.name}")


def _actual_type_ref(value: Value) -> TypeRef | None:
    return value.value if value.kind == "typeRef" else None


def _validate_actual_type_ref(
    diagnostics: list[SemanticDiagnostic],
    actual: TypeRef,
    registry: SemanticRegistry,
    symbols: dict[str, Declaration],
    line: int,
    column: int,
    subject: str,
) -> None:
    if actual.name in registry.combinators:
        combinator = registry.combinators[actual.name]
        if not combinator.arguments.accepts(len(actual.arguments)):
            diagnostics.append(SemanticDiagnostic("CORE-S020", line, column, f"{subject} uses {actual.name} with {len(actual.arguments)} type argument(s)", combinator.arguments.describe()))
        if combinator.behavior == "declaration-ref-kind" and actual.arguments:
            target = actual.arguments[-1].name
            if target not in symbols and target not in registry.declarations:
                diagnostics.append(SemanticDiagnostic("CORE-S021", line, column, f"unresolved declaration reference {target!r}", "resolvable declaration reference"))
    elif actual.name not in BUILTIN_TYPES and actual.name not in {"list", "TypeRef"} and actual.name not in symbols and actual.name not in registry.declarations:
        diagnostics.append(SemanticDiagnostic("CORE-S022", line, column, f"unknown TypeRef base {actual.name!r}", "builtin, declared type, declaration kind, or Core combinator"))
    for argument in actual.arguments:
        _validate_actual_type_ref(diagnostics, argument, registry, symbols, line, column, subject)


def _validate_value(
    diagnostics: list[SemanticDiagnostic],
    value: Value,
    expected: TypeRef,
    registry: SemanticRegistry,
    symbols: dict[str, Declaration],
    env: dict[str, TypeRef],
    line: int,
    column: int,
    subject: str,
) -> None:
    combinator = registry.combinators.get(expected.name)
    if combinator and combinator.behavior == "choice":
        alternatives = expected.arguments
        actual = _actual_type_ref(value)
        if actual is not None and actual.name in registry.combinators:
            specific = tuple(item for item in alternatives if item.name == actual.name)
            if specific:
                alternatives = specific
        snapshots: list[list[SemanticDiagnostic]] = []
        for alternative in alternatives:
            trial: list[SemanticDiagnostic] = []
            _validate_value(trial, value, alternative, registry, symbols, env, line, column, subject)
            if not trial:
                return
            snapshots.append(trial)
        diagnostics.append(SemanticDiagnostic("CORE-S010", line, column, f"{subject} does not match any Core choice alternative", _fmt_type(expected)))
        if snapshots:
            diagnostics.extend(snapshots[0][:1])
        return
    if combinator and combinator.behavior == "declaration-ref-kind":
        actual = _actual_type_ref(value)
        if actual is None or actual.name != expected.name or len(actual.arguments) != 1:
            diagnostics.append(SemanticDiagnostic("CORE-S011", line, column, f"{subject} is not a declaration reference", _fmt_type(expected)))
            return
        target_name = actual.arguments[0].name
        target = symbols.get(target_name)
        if target is None:
            diagnostics.append(SemanticDiagnostic("CORE-S012", line, column, f"unresolved reference {target_name!r}", f"ref<{expected.arguments[0].name}>"))
            return
        expected_kind = expected.arguments[0].name
        if target.kind != expected_kind:
            diagnostics.append(SemanticDiagnostic("CORE-S013", line, column, f"reference {target_name!r} resolves to kind {target.kind!r}", f"declaration kind {expected_kind}"))
        return
    if combinator and combinator.behavior == "expression":
        expression_text = value.raw if value.kind != "string" else str(value.value)
        inferred, error = infer_expression_type(expression_text, env)
        if error is not None:
            diagnostics.append(SemanticDiagnostic("CORE-S014", line, column, f"invalid expression for {subject}: {error}", _fmt_type(expected)))
            return
        target = expected.arguments[0].name if expected.arguments else "json"
        if inferred != target:
            diagnostics.append(SemanticDiagnostic("CORE-S015", line, column, f"expression for {subject} has inferred type {inferred!r}", f"expression<{target}>"))
        return
    if expected.name == "TypeRef":
        actual = _actual_type_ref(value)
        if actual is None:
            diagnostics.append(SemanticDiagnostic("CORE-S016", line, column, f"{subject} is not a TypeRef", "TypeRef"))
            return
        _validate_actual_type_ref(diagnostics, actual, registry, symbols, line, column, subject)
        return
    if expected.name == "list" and expected.arguments:
        if value.kind != "list":
            diagnostics.append(SemanticDiagnostic("CORE-S017", line, column, f"{subject} is not a list", _fmt_type(expected)))
        return
    primitive_ok = {
        "string": value.kind == "string",
        "bool": value.kind == "literal" and isinstance(value.value, bool),
        "int": value.kind == "number" and isinstance(value.value, int) and not isinstance(value.value, bool),
        "float": value.kind == "number",
        "json": True,
    }
    if expected.name in primitive_ok:
        if not primitive_ok[expected.name]:
            diagnostics.append(SemanticDiagnostic("CORE-S018", line, column, f"{subject} has incompatible value kind {value.kind!r}", _fmt_type(expected)))
        return
    actual = _actual_type_ref(value)
    if actual is not None:
        _validate_actual_type_ref(diagnostics, actual, registry, symbols, line, column, subject)
        if actual.name != expected.name:
            diagnostics.append(SemanticDiagnostic("CORE-S019", line, column, f"{subject} has TypeRef {_fmt_type(actual)!r}", _fmt_type(expected)))
        return
    diagnostics.append(SemanticDiagnostic("CORE-S019", line, column, f"{subject} does not match expected type", _fmt_type(expected)))


def validate_source(source: str, registry: SemanticRegistry) -> tuple[SemanticDiagnostic, ...]:
    program = parse_source(source)
    spans = _SourceSpans(source)
    symbols = {item.name: item for item in program.declarations if item.name is not None}
    diagnostics: list[SemanticDiagnostic] = []
    declaration_cursor = 0
    for declaration in program.declarations:
        decl_line, decl_column = spans.declaration(declaration, declaration_cursor)
        declaration_cursor = decl_line
        contract = registry.declarations.get(declaration.kind)
        if contract is None:
            diagnostics.append(SemanticDiagnostic("CORE-S000", decl_line, decl_column, f"unknown declaration kind {declaration.kind!r}", "Core-declared language kind"))
            continue
        _check_name_policy(diagnostics, contract.name_policy, declaration.name, decl_line, decl_column, f"declaration {declaration.kind}")
        _validate_arguments(diagnostics, declaration.arguments, contract.arguments, registry, symbols, {}, decl_line, decl_column, f"declaration {declaration.kind}")
        if declaration.result is not None and contract.result is None:
            diagnostics.append(SemanticDiagnostic("CORE-S005", decl_line, decl_column, f"declaration {declaration.kind} does not permit a result type", "no result type"))
        slot_by_type = {slot.body_type: slot for slot in contract.slots}
        ordered_positions = {slot.body_type: index for index, slot in enumerate(contract.slots) if slot.ordered}
        ordered_sequence = [slot.body_type for slot in contract.slots if slot.ordered]
        counts: dict[str, int] = {}
        names: dict[str, set[str]] = {}
        env: dict[str, TypeRef] = {}
        last_ordered_position: int | None = None
        body_cursor = decl_line
        for entry in declaration.body:
            line, column = spans.body(entry, body_cursor)
            body_cursor = line + 1
            slot = slot_by_type.get(entry.body_type)
            if slot is None:
                diagnostics.append(SemanticDiagnostic("CORE-S006", line, column, f"unknown body slot {entry.body_type!r} for {declaration.kind}", "Core-declared body slot"))
                continue
            counts[entry.body_type] = counts.get(entry.body_type, 0) + 1
            _check_name_policy(diagnostics, slot.name_policy, entry.name, line, column, f"body slot {entry.body_type}")
            if slot.ordered:
                position = ordered_positions[entry.body_type]
                if last_ordered_position is not None and position < last_ordered_position:
                    diagnostics.append(SemanticDiagnostic("CORE-S007", line, column, f"body slot {entry.body_type!r} appears out of Core-declared slot sequence", "ordered BodySlot sequence: " + " before ".join(ordered_sequence)))
                last_ordered_position = max(last_ordered_position or position, position)
            if slot.unique_by_name and entry.name is not None:
                seen = names.setdefault(entry.body_type, set())
                if entry.name in seen:
                    diagnostics.append(SemanticDiagnostic("CORE-S008", line, column, f"duplicate {entry.body_type} name {entry.name!r}", "uniqueByName"))
                seen.add(entry.name)
            if entry.value is None and slot.value_type is not None:
                diagnostics.append(SemanticDiagnostic("CORE-S009", line, column, f"body slot {entry.body_type!r} requires a value", _fmt_type(slot.value_type)))
            elif entry.value is not None and slot.value_type is None:
                diagnostics.append(SemanticDiagnostic("CORE-S009", line, column, f"body slot {entry.body_type!r} forbids a value", "no value"))
            elif entry.value is not None and slot.value_type is not None:
                _validate_value(diagnostics, entry.value, slot.value_type, registry, symbols, env, line, column, f"body slot {entry.body_type}")
                actual_type = _actual_type_ref(entry.value)
                if entry.name is not None and actual_type is not None:
                    env[entry.name] = actual_type
            allowed = set(slot.modifiers)
            modifier_counts: dict[str, int] = {}
            for modifier in entry.modifiers:
                modifier_counts[modifier.name] = modifier_counts.get(modifier.name, 0) + 1
                if modifier.name not in allowed:
                    diagnostics.append(SemanticDiagnostic("CORE-S030", line, column, f"modifier @{modifier.name} is not allowed on {entry.body_type}", "allowed modifiers: " + ", ".join(sorted(allowed))))
                    continue
                modifier_contract = registry.modifiers.get(modifier.name)
                if modifier_contract is None:
                    diagnostics.append(SemanticDiagnostic("CORE-S031", line, column, f"modifier @{modifier.name} has no Core definition", "Core-defined ModifierDefinition"))
                    continue
                if entry.body_type not in modifier_contract.targets:
                    diagnostics.append(SemanticDiagnostic("CORE-S032", line, column, f"modifier @{modifier.name} cannot target {entry.body_type}", "targets: " + ", ".join(modifier_contract.targets)))
                _validate_arguments(diagnostics, modifier.arguments, modifier_contract.arguments, registry, symbols, env, line, column, f"modifier @{modifier.name}")
            for modifier_name in allowed:
                modifier_contract = registry.modifiers.get(modifier_name)
                if modifier_contract is None:
                    continue
                count = modifier_counts.get(modifier_name, 0)
                if not modifier_contract.cardinality.accepts(count):
                    diagnostics.append(SemanticDiagnostic("CORE-S033", line, column, f"modifier @{modifier_name} occurs {count} time(s)", modifier_contract.cardinality.describe()))
        for slot in contract.slots:
            count = counts.get(slot.body_type, 0)
            if not slot.cardinality.accepts(count):
                diagnostics.append(SemanticDiagnostic("CORE-S034", decl_line, decl_column, f"body slot {slot.body_type!r} occurs {count} time(s)", slot.cardinality.describe()))
    diagnostics.sort(key=lambda item: (item.line, item.column, item.code, item.message))
    return tuple(diagnostics)


_EXPR_TOKEN = re.compile(r"\s*(?:(true|false)|(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\&\&|\|\||==|!=|!|\(|\)))")


def _expression_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    position = 0
    while position < len(text):
        match = _EXPR_TOKEN.match(text, position)
        if match is None:
            raise ValueError(f"unsupported token near {text[position:position + 12]!r}")
        tokens.append(next(group for group in match.groups() if group is not None))
        position = match.end()
    return tokens


class _ExpressionParser:
    def __init__(self, tokens: list[str], env: dict[str, TypeRef]) -> None:
        self.tokens = tokens
        self.env = env
        self.index = 0

    def current(self) -> str | None:
        return None if self.index >= len(self.tokens) else self.tokens[self.index]

    def take(self) -> str:
        token = self.current()
        if token is None:
            raise ValueError("unexpected end of expression")
        self.index += 1
        return token

    def parse(self) -> str:
        result = self.or_expr()
        if self.current() is not None:
            raise ValueError(f"unexpected token {self.current()!r}")
        return result

    def or_expr(self) -> str:
        left = self.and_expr()
        while self.current() == "||":
            self.take()
            right = self.and_expr()
            self.require_bool(left, "||")
            self.require_bool(right, "||")
            left = "bool"
        return left

    def and_expr(self) -> str:
        left = self.eq_expr()
        while self.current() == "&&":
            self.take()
            right = self.eq_expr()
            self.require_bool(left, "&&")
            self.require_bool(right, "&&")
            left = "bool"
        return left

    def eq_expr(self) -> str:
        left = self.unary()
        while self.current() in {"==", "!="}:
            op = self.take()
            right = self.unary()
            if left != right:
                raise ValueError(f"{op} compares incompatible types {left} and {right}")
            left = "bool"
        return left

    def unary(self) -> str:
        if self.current() == "!":
            self.take()
            result = self.unary()
            self.require_bool(result, "!")
            return "bool"
        return self.primary()

    def primary(self) -> str:
        token = self.take()
        if token == "(":
            result = self.or_expr()
            if self.take() != ")":
                raise ValueError("expected closing parenthesis")
            return result
        if token in {"true", "false"}:
            return "bool"
        if re.fullmatch(r"\d+", token):
            return "int"
        if re.fullmatch(r"\d+\.\d+", token):
            return "float"
        if token not in self.env:
            raise ValueError(f"unresolved expression name {token!r}")
        type_ref = self.env[token]
        if type_ref.name == "ref":
            raise ValueError(f"expression name {token!r} is a declaration reference, not a scalar")
        return type_ref.name

    @staticmethod
    def require_bool(value: str, operator: str) -> None:
        if value != "bool":
            raise ValueError(f"operator {operator} requires bool, found {value}")


def infer_expression_type(text: str, env: dict[str, TypeRef]) -> tuple[str | None, str | None]:
    try:
        tokens = _expression_tokens(text)
        if not tokens:
            raise ValueError("empty expression")
        return _ExpressionParser(tokens, env).parse(), None
    except ValueError as exc:
        return None, str(exc)
