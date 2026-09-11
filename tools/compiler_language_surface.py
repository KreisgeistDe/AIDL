"""M10.1 compatibility bridge behind the existing legacy parser.

The parser remains the source-language recognizer. This module loads
``spec/language-surface-v1.json`` as the only declaration/body/modifier
construction contract and projects representative legacy parser nodes into the
frozen semantic model.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

try:
    from .aidl_parser import Node, parse_text
except ImportError:  # pragma: no cover
    from aidl_parser import Node, parse_text


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "spec" / "language-surface-v1.json"
NORMALIZATION_VERSION = "aidl.m10.1-normalized/v2"


@dataclass(frozen=True)
class BridgeDiagnostic:
    code: str
    message: str
    severity: str = "error"

    def to_json(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass(frozen=True)
class TypeRef:
    kind: str
    optional: bool = False
    name: str | None = None
    element: "TypeRef | None" = None
    target: str | None = None
    projection: str | None = None
    resolved_type: str | None = None

    def semantic(self) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": self.kind, "optional": self.optional}
        for key in ("name", "target", "projection", "resolved_type"):
            item = getattr(self, key)
            if item is not None:
                value[key] = item
        if self.element is not None:
            value["element"] = self.element.semantic()
        return value


@dataclass(frozen=True)
class ModifierCall:
    name: str
    target: str
    argument_mode: str
    args: tuple[Any, ...] = ()

    def semantic(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target,
            "argument_mode": self.argument_mode,
            "args": list(self.args),
        }


@dataclass(frozen=True)
class OperationParameter:
    name: str
    type_ref: TypeRef
    modifiers: tuple[ModifierCall, ...] = ()

    def semantic(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type_ref.semantic(),
        }
        if self.modifiers:
            result["modifiers"] = [item.semantic() for item in self.modifiers]
        return result


@dataclass(frozen=True)
class HeaderArg:
    name: str
    value_mode: str
    value: Any

    def semantic(self) -> dict[str, Any]:
        return {"name": self.name, "value_mode": self.value_mode, "value": _jsonable(self.value)}


@dataclass(frozen=True)
class BodySlot:
    slot_id: str
    name: str | None
    value_mode: str
    value: Any
    modifiers: tuple[ModifierCall, ...] = ()

    def semantic(self) -> dict[str, Any]:
        result = {
            "slot": self.slot_id,
            "name": self.name,
            "value_mode": self.value_mode,
            "value": _jsonable(self.value),
        }
        if self.modifiers:
            result["modifiers"] = [item.semantic() for item in self.modifiers]
        return result


@dataclass(frozen=True)
class Declaration:
    kind: str
    name: str | None
    name_policy: str
    exported: bool
    header_args: tuple[HeaderArg, ...] = ()
    result_type: TypeRef | None = None
    body_slots: tuple[BodySlot, ...] = ()
    modifiers: tuple[ModifierCall, ...] = ()
    facts: Mapping[str, Any] = field(default_factory=dict)

    def semantic(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "name": self.name,
            "name_policy": self.name_policy,
            "exported": self.exported,
            "header_args": [item.semantic() for item in self.header_args],
            "body_slots": [item.semantic() for item in self.body_slots],
            "modifiers": [item.semantic() for item in self.modifiers],
        }
        if self.result_type is not None:
            result["result_type"] = self.result_type.semantic()
        if self.facts:
            result["facts"] = _jsonable(dict(self.facts))
        return result

    def semantic_json(self) -> str:
        return _stable_json(self.semantic())

    def semantic_hash(self) -> str:
        return hashlib.sha256(self.semantic_json().encode()).hexdigest()


@dataclass(frozen=True)
class Document:
    module: str | None
    imports: tuple[str, ...]
    declarations: tuple[Declaration, ...]

    def semantic(self) -> dict[str, Any]:
        return {
            "normalization_version": NORMALIZATION_VERSION,
            "module": self.module,
            "imports": list(self.imports),
            "declarations": [item.semantic() for item in self.declarations],
        }

    def semantic_json(self) -> str:
        return _stable_json(self.semantic())

    def semantic_hash(self) -> str:
        return hashlib.sha256(self.semantic_json().encode()).hexdigest()


@dataclass(frozen=True)
class BridgeResult:
    document: Document
    diagnostics: tuple[BridgeDiagnostic, ...]
    parser_diagnostics: tuple[Any, ...]

    @property
    def ok(self) -> bool:
        return not self.parser_diagnostics and not any(item.severity == "error" for item in self.diagnostics)


class UnsupportedMigration(ValueError):
    pass


class LanguageSurfaceBridge:
    """Parser-AST adapter driven by the frozen M10.1 language-surface contract."""

    def __init__(
        self,
        contract_path: Path = CONTRACT_PATH,
        *,
        reference_projections: Mapping[str, tuple[str, str | None, str | None]] | None = None,
    ) -> None:
        self.contract = json.loads(contract_path.read_text(encoding="utf-8"))
        if self.contract.get("authority") != "M10.1":
            raise ValueError("language-surface-v1 authority must be M10.1")
        self.kinds = {item["kind"]: item for item in self.contract["declaration_kinds"]}
        self.modifiers = {item["name"]: item for item in self.contract["modifiers"]}
        self.reference_projections = dict(reference_projections or {})

    def normalize_text(self, text: str) -> BridgeResult:
        program, parser_diagnostics, _ = parse_text(text)
        document, diagnostics = self.normalize_program(program)
        return BridgeResult(document, tuple(diagnostics), tuple(parser_diagnostics))

    def normalize_program(self, program: Node) -> tuple[Document, list[BridgeDiagnostic]]:
        module: str | None = None
        imports: list[str] = []
        declarations: list[Declaration] = []
        diagnostics: list[BridgeDiagnostic] = []
        for node in program.children:
            if node.kind == "module":
                module = module or node.name
            elif node.kind == "import":
                if node.name:
                    imports.append(node.name)
            else:
                declaration, items = self.normalize_declaration(node)
                declarations.append(declaration)
                diagnostics.extend(items)
        return Document(module, tuple(imports), tuple(declarations)), diagnostics

    def normalize_declaration(self, node: Node) -> tuple[Declaration, list[BridgeDiagnostic]]:
        diagnostics: list[BridgeDiagnostic] = []
        kind = "alias" if node.kind == "opaque" else node.kind
        schema = self.kinds.get(kind)
        if schema is None:
            diagnostics.append(BridgeDiagnostic("AIDL-N001", f"unknown frozen declaration kind: {kind}"))
            return Declaration(kind, node.name, "optional", bool(node.attrs.get("exported"))), diagnostics

        policy = schema["name_policy"]
        if policy == "required" and not node.name:
            diagnostics.append(BridgeDiagnostic("AIDL-N002", f"{kind} requires a name"))
        if policy == "none" and node.name:
            diagnostics.append(BridgeDiagnostic("AIDL-N003", f"{kind} forbids a name"))

        headers = self._headers(node, kind, schema, diagnostics)
        body = self._body(node, kind, schema, diagnostics)
        annotations = tuple(self._annotations(node, kind, diagnostics))
        result_type = (
            self.type_ref(str(node.attrs["returns"]), diagnostics)
            if schema.get("result_type") and node.attrs.get("returns")
            else None
        )
        facts: dict[str, Any] = {}
        if kind == "alias":
            facts["opacity"] = node.kind == "opaque"
            if node.attrs.get("type"):
                facts["aliased_type"] = self.type_ref(str(node.attrs["type"]), diagnostics)
        if node.attrs.get("parameters") and not any(
            item.name == "parameters" and item.value_mode == "parameter_list" for item in headers
        ):
            # Kept only as fail-closed evidence when the contract cannot normalize
            # the legacy signature losslessly.
            facts["legacy_parameters"] = _surface(str(node.attrs["parameters"]))

        declaration = Declaration(
            kind=kind,
            name=node.name,
            name_policy=policy,
            exported=bool(node.attrs.get("exported")),
            header_args=tuple(headers),
            result_type=result_type,
            body_slots=tuple(body),
            modifiers=annotations,
            facts=facts,
        )
        self._validate_slots(declaration, schema, diagnostics)
        return declaration, diagnostics

    def _headers(
        self,
        node: Node,
        kind: str,
        schema: Mapping[str, Any],
        diagnostics: list[BridgeDiagnostic],
    ) -> list[HeaderArg]:
        source: dict[str, Any] = {}
        if kind == "migration":
            source = {"fromVersion": node.attrs.get("from"), "toVersion": node.attrs.get("to")}
        elif kind == "client":
            source = {"service": node.attrs.get("for")}
        elif kind == "consumer":
            source = {"topic": node.attrs.get("on"), "messageType": node.attrs.get("from")}
        elif kind == "projection":
            source = {"sources": node.attrs.get("from"), "target": node.attrs.get("into")}
        elif kind in {"query", "mutation"}:
            source = {"parameters": node.attrs.get("parameters")}

        result: list[HeaderArg] = []
        for spec in schema.get("header_args", []):
            raw = source.get(spec["name"])
            if raw in (None, ""):
                if spec["occurrence"]["min"]:
                    diagnostics.append(BridgeDiagnostic("AIDL-N004", f"{kind} misses header fact {spec['name']}"))
                continue
            mode = spec["value_mode"]
            if mode == "parameter_list":
                value = self._operation_parameters(str(raw), kind, spec, diagnostics)
                if value:
                    result.append(HeaderArg(spec["name"], mode, value))
                continue
            value = self.type_ref(str(raw), diagnostics) if mode == "type_ref" else _surface(str(raw))
            result.append(HeaderArg(spec["name"], mode, value))
        return result

    def _operation_parameters(
        self,
        raw: str,
        kind: str,
        spec: Mapping[str, Any],
        diagnostics: list[BridgeDiagnostic],
    ) -> tuple[OperationParameter, ...]:
        text = raw.strip()
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()
        if not text:
            return ()

        parameter_spec = spec.get("parameter", {})
        allowed_modifiers = tuple(str(item) for item in parameter_spec.get("modifiers", []))
        parameters: list[OperationParameter] = []
        seen: set[str] = set()
        for raw_parameter in _split_commas(text):
            part = raw_parameter.strip()
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)", part, re.S)
            if not match:
                diagnostics.append(
                    BridgeDiagnostic("AIDL-N015", f"{kind} parameter is not losslessly typed: {part}")
                )
                continue
            name, tail = match.groups()
            if name in seen:
                diagnostics.append(BridgeDiagnostic("AIDL-N015", f"duplicate {kind} parameter: {name}"))
            seen.add(name)

            words = _words(tail)
            modifier_index = next(
                (index for index, word in enumerate(words) if word in self.modifiers),
                len(words),
            )
            type_text = " ".join(words[:modifier_index]).strip()
            if not type_text:
                diagnostics.append(BridgeDiagnostic("AIDL-N015", f"{kind} parameter {name} has no type"))
                continue

            modifiers: list[ModifierCall] = []
            index = modifier_index
            while index < len(words):
                modifier_name = words[index]
                modifier_spec = self.modifiers.get(modifier_name)
                if modifier_spec is None or modifier_name not in allowed_modifiers:
                    diagnostics.append(
                        BridgeDiagnostic(
                            "AIDL-N015",
                            f"{kind} parameter {name} uses unsupported modifier {modifier_name}",
                        )
                    )
                    break
                minimum = int(modifier_spec["arity"]["min"])
                maximum = modifier_spec["arity"]["max"]
                if modifier_spec.get("argument_mode") == "expression" and minimum == 1 and maximum == 1:
                    argument_text = " ".join(words[index + 1:]).strip()
                    args = (argument_text,) if argument_text else ()
                    index = len(words)
                else:
                    take = minimum
                    args = tuple(words[index + 1:index + 1 + take])
                    index += 1 + take
                modifiers.append(self._modifier(modifier_name, f"{kind}.parameter", args, diagnostics))

            parameters.append(
                OperationParameter(
                    name=name,
                    type_ref=self.type_ref(type_text, diagnostics),
                    modifiers=tuple(modifiers),
                )
            )
        return tuple(parameters)

    def _body(
        self,
        node: Node,
        kind: str,
        schema: Mapping[str, Any],
        diagnostics: list[BridgeDiagnostic],
    ) -> list[BodySlot]:
        specs = {item["id"]: item for item in schema.get("body_slots", [])}
        result: list[BodySlot] = []

        if kind == "enum" and "case" in specs:
            for item in node.attrs.get("enumCases", []):
                if item.get("malformed"):
                    diagnostics.append(BridgeDiagnostic("AIDL-N005", f"malformed enum case: {item.get('raw', '')}"))
                    continue
                wire = item.get("assignedValue")
                result.append(
                    BodySlot(
                        "case",
                        item.get("name"),
                        "enum_case",
                        {"wire_literal": _literal(wire) if wire is not None else None},
                    )
                )
            return result

        for child in node.children:
            text = _surface(child.name or "")
            if not text:
                continue
            if kind == "entity" and "field" in specs and re.match(r"^[A-Za-z_]\w*\s*:", text):
                slot = self._entity_field(text, diagnostics)
                if slot:
                    result.append(slot)
                continue
            if kind == "app" and "profile" in specs and text.startswith("profile "):
                match = re.fullmatch(r"profile\s+([A-Za-z_]\w*)\s+version\s+(-?\d+)", text)
                if match:
                    result.append(
                        BodySlot(
                            "profile",
                            match.group(1),
                            "block",
                            {"slots": [{"slot": "version", "value_mode": "literal", "value": int(match.group(2))}]},
                        )
                    )
                else:
                    diagnostics.append(BridgeDiagnostic("AIDL-N011", f"unsupported profile shape: {text}"))
                continue
            if kind == "query" and "read" in specs and (text.startswith("read:") or text.startswith("read ")):
                result.append(BodySlot("read", None, "expression", _after_keyword(text, "read")))
                continue
            diagnostics.append(BridgeDiagnostic("AIDL-N010", f"legacy body clause not normalized yet: {text}", "warning"))
        return result

    def _entity_field(self, text: str, diagnostics: list[BridgeDiagnostic]) -> BodySlot | None:
        match = re.match(r"^([A-Za-z_]\w*)\s*:\s*(.+)$", text)
        if not match:
            return None
        name, tail = match.groups()
        words = _words(tail)
        modifier_index = next((i for i, word in enumerate(words) if word in self.modifiers), len(words))
        type_text = " ".join(words[:modifier_index])
        modifier_words = words[modifier_index:]
        modifiers: list[ModifierCall] = []
        index = 0
        while index < len(modifier_words):
            modifier_name = modifier_words[index]
            spec = self.modifiers.get(modifier_name)
            if spec is None:
                diagnostics.append(BridgeDiagnostic("AIDL-N010", f"legacy modifier not normalized yet: {modifier_name}", "warning"))
                index += 1
                continue
            required = int(spec["arity"]["min"])
            if spec.get("argument_mode") == "expression" and required == 1:
                args = (" ".join(modifier_words[index + 1:]),) if index + 1 < len(modifier_words) else ()
                index = len(modifier_words)
            else:
                args = tuple(modifier_words[index + 1:index + 1 + required])
                index += 1 + required
            modifiers.append(self._modifier(modifier_name, "entity.field", args, diagnostics))
        return BodySlot("field", name, "type_ref", self.type_ref(type_text, diagnostics), tuple(modifiers))

    def _annotations(self, node: Node, target: str, diagnostics: list[BridgeDiagnostic]) -> list[ModifierCall]:
        result: list[ModifierCall] = []
        for item in node.attrs.get("annotations", []):
            result.append(self._modifier(str(item.get("name", "")), target, _args(item.get("arguments")), diagnostics))
        return result

    def _modifier(self, name: str, target: str, args: tuple[Any, ...], diagnostics: list[BridgeDiagnostic]) -> ModifierCall:
        spec = self.modifiers.get(name)
        if spec is None:
            diagnostics.append(BridgeDiagnostic("AIDL-N007", f"modifier not declared by frozen contract: {name}"))
            return ModifierCall(name, target, "unknown", args)
        if target not in spec["targets"]:
            diagnostics.append(BridgeDiagnostic("AIDL-N008", f"modifier {name} is not valid on {target}"))
        minimum, maximum = int(spec["arity"]["min"]), spec["arity"]["max"]
        if len(args) < minimum or (maximum is not None and len(args) > int(maximum)):
            diagnostics.append(BridgeDiagnostic("AIDL-N009", f"modifier {name} expects arity {minimum}..{maximum}; got {len(args)}"))
        mode = spec["argument_mode"]
        normalized = tuple(_literal(value) if mode == "literal" else _surface(str(value)) for value in args)
        return ModifierCall(name, target, mode, normalized)

    def type_ref(self, raw: str, diagnostics: list[BridgeDiagnostic] | None = None) -> TypeRef:
        diagnostics = diagnostics if diagnostics is not None else []
        text = _type_text(raw)
        optional = text.endswith("?")
        if optional:
            text = text[:-1]
        if text.startswith("[") and text.endswith("]"):
            return TypeRef("list", optional, element=self.type_ref(text[1:-1], diagnostics))
        if text.startswith("ref "):
            return self._reference(text[4:].strip(), optional, diagnostics)
        if text in self.reference_projections:
            return self._reference(text, optional, diagnostics)
        scalars = {"string", "int", "decimal", "bool", "uuid", "date", "datetime", "duration", "revision", "email", "url", "bytes"}
        return TypeRef("scalar" if text in scalars else "named", optional, name=text)

    def _reference(self, text: str, optional: bool, diagnostics: list[BridgeDiagnostic]) -> TypeRef:
        if text in self.reference_projections:
            target, projection, resolved = self.reference_projections[text]
            return TypeRef("reference", optional, target=target, projection=projection, resolved_type=resolved)
        if "." in text:
            target, projection = text.rsplit(".", 1)
            diagnostics.append(BridgeDiagnostic("AIDL-N012", f"reference projection {text} needs resolver evidence"))
            return TypeRef("reference", optional, target=target, projection=projection)
        return TypeRef("reference", optional, target=text)

    def _validate_slots(self, declaration: Declaration, schema: Mapping[str, Any], diagnostics: list[BridgeDiagnostic]) -> None:
        grouped: dict[str, list[BodySlot]] = {}
        for slot in declaration.body_slots:
            grouped.setdefault(slot.slot_id, []).append(slot)
        for spec in schema.get("body_slots", []):
            values = grouped.get(spec["id"], [])
            minimum, maximum = int(spec["occurrence"]["min"]), spec["occurrence"]["max"]
            if len(values) < minimum or (maximum is not None and len(values) > int(maximum)):
                diagnostics.append(BridgeDiagnostic("AIDL-N006", f"{declaration.kind}.{spec['id']} occurrence {minimum}..{maximum}; got {len(values)}"))
            if spec.get("unique"):
                names = [item.name for item in values if item.name is not None]
                if len(names) != len(set(names)):
                    diagnostics.append(BridgeDiagnostic("AIDL-N005", f"duplicate unique {declaration.kind}.{spec['id']} name"))

    def format_legacy(self, declaration: Declaration) -> str:
        """Same-version canonicalization; it never emits target-version syntax."""
        prefix = _annotation_prefix(declaration.modifiers) + ("export " if declaration.exported else "")
        headers = {item.name: item.value for item in declaration.header_args}
        if declaration.kind == "migration":
            return f'{prefix}migration {declaration.name} from "{headers["fromVersion"]}" to "{headers["toVersion"]}" {{}}\n'
        if declaration.kind == "client":
            return f'{prefix}client {declaration.name} for {headers["service"]} {{}}\n'
        if declaration.kind == "consumer":
            return f'{prefix}consumer {declaration.name} on {headers["topic"]} from {headers["messageType"]} {{}}\n'
        if declaration.kind == "projection":
            return f'{prefix}projection {declaration.name} from {headers["sources"]} into {headers["target"]} {{}}\n'
        if declaration.kind == "alias":
            aliased = declaration.facts.get("aliased_type")
            if not isinstance(aliased, TypeRef):
                raise UnsupportedMigration("alias formatter requires aliased_type")
            keyword = "opaque" if declaration.facts.get("opacity") else "alias"
            return f"{prefix}{keyword} {declaration.name} = {_format_type(aliased)}\n"
        if declaration.kind == "entity":
            lines = [f"{prefix}entity {declaration.name} {{"]
            for slot in declaration.body_slots:
                if slot.slot_id != "field" or not isinstance(slot.value, TypeRef):
                    raise UnsupportedMigration("entity formatter prototype supports fields only")
                modifiers = " ".join(_format_modifier(item) for item in slot.modifiers)
                lines.append(f"  {slot.name}: {_format_type(slot.value)}" + (f" {modifiers}" if modifiers else ""))
            return "\n".join(lines + ["}"]) + "\n"
        if declaration.kind == "enum":
            cases = []
            for slot in declaration.body_slots:
                wire = slot.value.get("wire_literal")
                cases.append(str(slot.name) if wire is None else f"{slot.name} = {json.dumps(wire)}")
            return f"{prefix}enum {declaration.name} {{ {', '.join(cases)} }}\n"
        if declaration.kind == "app":
            lines = [f"{prefix}app {declaration.name} {{"]
            for slot in declaration.body_slots:
                version = slot.value["slots"][0]["value"]
                lines.append(f"  profile {slot.name} version {version}")
            return "\n".join(lines + ["}"]) + "\n"
        if declaration.kind in {"query", "mutation"}:
            result = f" -> {_format_type(declaration.result_type)}" if declaration.result_type else ""
            parameters = _format_parameter_list(headers.get("parameters", ()))
            lines = [f"{prefix}{declaration.kind} {declaration.name}({parameters}){result} {{"]
            if declaration.kind == "query":
                lines += [f"  read: {slot.value}" for slot in declaration.body_slots if slot.slot_id == "read"]
            return "\n".join(lines + ["}"]) + "\n"
        raise UnsupportedMigration(f"same-version formatter does not support {declaration.kind}")

    def migrate_to_canonical_preview(self, declaration: Declaration) -> str:
        """Explicit target-version preview. Never used by ``format_legacy``."""
        prefix = _annotation_prefix(declaration.modifiers) + ("export " if declaration.exported else "")
        if declaration.kind in {"migration", "client", "consumer", "projection"}:
            args = ", ".join(f"{item.name}: {_format_header(item)}" for item in declaration.header_args)
            return f"{prefix}{declaration.kind} {declaration.name}({args}) {{}}\n"
        if declaration.kind == "entity":
            lines = [f"{prefix}entity {declaration.name} {{"]
            for slot in declaration.body_slots:
                if not isinstance(slot.value, TypeRef):
                    raise UnsupportedMigration("non-type entity slot is outside prototype")
                modifiers = " ".join(_format_modifier(item) for item in slot.modifiers)
                lines.append(f"  field {slot.name}: {_format_type(slot.value)}" + (f" {modifiers}" if modifiers else ""))
            return "\n".join(lines + ["}"]) + "\n"
        if declaration.kind == "enum":
            lines = [f"{prefix}enum {declaration.name} {{"]
            for slot in declaration.body_slots:
                wire = slot.value.get("wire_literal")
                lines.append(f"  case {slot.name}" + ("" if wire is None else f" = {json.dumps(wire)}"))
            return "\n".join(lines + ["}"]) + "\n"
        if declaration.kind == "app":
            lines = [f"{prefix}app {declaration.name} {{"]
            for slot in declaration.body_slots:
                version = slot.value["slots"][0]["value"]
                lines += [f"  profile {slot.name} {{", f"    version: {version}", "  }"]
            return "\n".join(lines + ["}"]) + "\n"
        if declaration.kind in {"query", "mutation"}:
            parameters = next((item.value for item in declaration.header_args if item.name == "parameters"), ())
            if parameters:
                raise UnsupportedMigration("operation parameter target syntax is not yet a production parser surface")
            result = f" -> {_format_type(declaration.result_type)}" if declaration.result_type else ""
            lines = [f"{prefix}{declaration.kind} {declaration.name}{result} {{"]
            if declaration.kind == "query":
                lines += [f"  read: {slot.value}" for slot in declaration.body_slots if slot.slot_id == "read"]
            return "\n".join(lines + ["}"]) + "\n"
        if declaration.kind == "alias" and declaration.facts.get("opacity"):
            raise UnsupportedMigration("opaque alias semantics normalize, but the frozen contract has no canonical opacity slot")
        raise UnsupportedMigration(f"canonical preview does not support {declaration.kind}")


def _jsonable(value: Any) -> Any:
    if isinstance(value, TypeRef):
        return value.semantic()
    if isinstance(value, OperationParameter):
        return value.semantic()
    if isinstance(value, ModifierCall):
        return value.semantic()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _surface(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"\s*\.\s*", ".", text)
    text = re.sub(r"\s*\?\s*", "?", text)
    text = re.sub(r"\s*:\s*", ": ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    return text.strip()


def _type_text(text: str) -> str:
    text = _surface(text)
    text = re.sub(r"\[\s*", "[", text)
    text = re.sub(r"\s*\]", "]", text)
    return text


def _literal(value: Any) -> Any:
    if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    return value


def _args(raw: Any) -> tuple[Any, ...]:
    if raw is None:
        return ()
    text = str(raw).strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    if not text:
        return ()
    return tuple(_literal(item.strip()) for item in _split_commas(text))


def _split_commas(text: str) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False
    close = {")": "(", "]": "[", "}": "{", ">": "<"}
    stack: list[str] = []
    for char in text:
        if quote is not None:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            current.append(char)
        elif char in "([{<":
            stack.append(char)
            depth += 1
            current.append(char)
        elif char in ")]}>":
            if stack and stack[-1] == close[char]:
                stack.pop()
                depth = max(0, depth - 1)
            current.append(char)
        elif char == "," and depth == 0:
            result.append("".join(current))
            current = []
        else:
            current.append(char)
    result.append("".join(current))
    return result


def _words(text: str) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False
    for char in text:
        if quote is not None:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            current.append(char)
            continue
        if char in "([{<":
            depth += 1
        elif char in ")]}>" :
            depth = max(0, depth - 1)
        if char.isspace() and depth == 0:
            if current:
                result.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        result.append("".join(current))
    return result


def _after_keyword(text: str, keyword: str) -> str:
    value = text[len(keyword):].lstrip()
    return value[1:].lstrip() if value.startswith(":") else value


def _annotation_prefix(modifiers: tuple[ModifierCall, ...]) -> str:
    lines = []
    for item in modifiers:
        args = ", ".join(json.dumps(value) if isinstance(value, str) else str(value) for value in item.args)
        lines.append(f"@{item.name}" + (f"({args})" if item.args else ""))
    return "".join(line + "\n" for line in lines)


def _format_type(value: TypeRef | None) -> str:
    if value is None:
        return ""
    if value.kind == "list" and value.element:
        base = f"[{_format_type(value.element)}]"
    elif value.kind == "reference":
        base = f"ref {value.target or ''}" + (f".{value.projection}" if value.projection else "")
    else:
        base = value.name or value.kind
    return base + ("?" if value.optional else "")


def _format_modifier(value: ModifierCall) -> str:
    if not value.args:
        return value.name
    return value.name + " " + " ".join(str(item) for item in value.args)


def _format_parameter_list(value: Any) -> str:
    if not isinstance(value, (list, tuple)):
        return ""
    result = []
    for item in value:
        if not isinstance(item, OperationParameter):
            continue
        modifiers = " ".join(_format_modifier(modifier) for modifier in item.modifiers)
        text = f"{item.name}: {_format_type(item.type_ref)}"
        result.append(text + (f" {modifiers}" if modifiers else ""))
    return ", ".join(result)


def _format_header(value: HeaderArg) -> str:
    if value.value_mode == "literal":
        return json.dumps(value.value, ensure_ascii=False)
    if isinstance(value.value, TypeRef):
        return _format_type(value.value)
    return str(value.value)
