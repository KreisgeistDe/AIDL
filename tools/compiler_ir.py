from __future__ import annotations

import re
from typing import Any, Mapping

from tools.aidl_parser import Node
from tools.compiler_diagnostics import CompilerAnalysis
from tools.compiler_project import CompilerDeclarationName
from tools.ir_identity import IrIdentityError, declaration_identity
from tools.ir_semantic_hash import apply_semantic_hashes
from tools.ir_semantic_projection import prepare_canonical_ir

IR_VERSION = "0.3.0"
_ZERO_HASH = "sha256:" + "0" * 64
_DECL_KINDS = {
    "enum", "alias", "opaque", "value", "entity", "view", "error",
    "query", "mutation", "api", "event", "topic", "consumer",
    "workflow", "saga", "task",
}
_SCALARS = {"string", "int", "decimal", "bool", "uuid", "date", "datetime", "duration", "revision", "email", "url", "bytes"}


class IrBuildError(ValueError):
    pass


def _text(node: Node) -> str:
    return (node.name or "").strip()


def _value(node: Node, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}(?:\s*:\s*|\s+)(.*)$", re.S)
    for child in node.children:
        match = pattern.match(_text(child))
        if match:
            return match.group(1).strip()
    return None


def _values(node: Node, key: str) -> list[str]:
    pattern = re.compile(rf"^{re.escape(key)}(?:\s*:\s*|\s+)(.*)$", re.S)
    return [match.group(1).strip() for child in node.children if (match := pattern.match(_text(child)))]


def _block(node: Node, key: str) -> Node | None:
    for child in node.children:
        if child.kind != "blockClause":
            continue
        head = _text(child)
        if head in {key, f"{key}:"} or head.startswith(f"{key} "):
            return child
    return None


def _split(value: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    stack: list[str] = []
    quote: str | None = None
    pairs = {")": "(", "]": "[", "}": "{", ">": "<"}
    for char in value:
        if quote:
            buf.append(char)
            if char == quote and (len(buf) < 2 or buf[-2] != "\\"):
                quote = None
        elif char in {'"', "'"}:
            quote = char
            buf.append(char)
        elif char in "([{<":
            stack.append(char)
            buf.append(char)
        elif char in ")]}>":
            if stack and stack[-1] == pairs[char]:
                stack.pop()
            buf.append(char)
        elif char == "," and not stack:
            if "".join(buf).strip():
                parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(char)
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


def _list(value: str | None) -> list[str]:
    if not value:
        return []
    value = value.strip()
    return _split(value[1:-1]) if value.startswith("[") and value.endswith("]") else []


def _clean(ref: str) -> str:
    ref = re.sub(r"^(query|mutation|consumer|workflow|saga|task|service|resource|api|event|topic)\s+", "", ref.strip())
    return re.sub(r"\s*\.\s*", ".", ref)


def _unquote(value: str) -> str:
    value = value.strip()
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] == '"' else value


def _ms(value: str) -> int:
    match = re.fullmatch(r"(\d+)(ms|s|m|h|d)", value.strip())
    if not match:
        raise IrBuildError(f"unsupported duration '{value}'")
    return int(match.group(1)) * {"ms": 1, "s": 1000, "m": 60000, "h": 3600000, "d": 86400000}[match.group(2)]


def _major(item: CompilerDeclarationName) -> int:
    if item.declaration.kind == "event":
        version = item.declaration.node.attrs.get("version")
        if isinstance(version, str) and version.isdigit() and int(version) > 0:
            return int(version)
    if item.declaration.kind == "api":
        version = _value(item.declaration.node, "version")
        if version and version.isdigit() and int(version) > 0:
            return int(version)
    return 1


class _Resolver:
    def __init__(self, analysis: CompilerAnalysis) -> None:
        self.project = analysis.project
        self.ids: dict[int, dict[str, str]] = {}
        self.by_fqn: dict[str, CompilerDeclarationName] = {}
        self.by_name: dict[str, list[CompilerDeclarationName]] = {}
        for item in self.project.declaration_names:
            if item.fully_qualified_name:
                self.by_fqn.setdefault(item.fully_qualified_name, item)
            if item.declaration.name:
                self.by_name.setdefault(item.declaration.name, []).append(item)
            if item.fully_qualified_name and item.declaration.name and item.document.module and item.document.module.name:
                try:
                    self.ids[id(item)] = declaration_identity(item, _major(item)).as_ir_fields()
                except IrIdentityError as exc:
                    raise IrBuildError(str(exc)) from exc

    def identity(self, item: CompilerDeclarationName) -> dict[str, str]:
        if id(item) not in self.ids:
            raise IrBuildError(f"declaration '{item.declaration.name or '<unnamed>'}' has no IR identity")
        return dict(self.ids[id(item)])

    def resolve(self, source: CompilerDeclarationName | None, ref: str, kinds: set[str] | None = None) -> CompilerDeclarationName | None:
        ref = _clean(ref)
        exact = self.by_fqn.get(ref)
        if exact and (kinds is None or exact.declaration.kind in kinds):
            return exact
        candidates: list[CompilerDeclarationName] = []
        seen: set[int] = set()
        def add(item: CompilerDeclarationName) -> None:
            if (kinds is None or item.declaration.kind in kinds) and id(item) not in seen:
                seen.add(id(item)); candidates.append(item)
        if source and "." not in ref:
            if source.document.module and source.document.module.name:
                local = self.by_fqn.get(f"{source.document.module.name}.{ref}")
                if local:
                    add(local)
            for resolution in self.project.import_resolutions:
                if resolution.document is source.document:
                    for item in resolution.declarations:
                        if item.declaration.name == ref:
                            add(item)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return None
        for item in self.by_name.get(ref, []):
            add(item)
        return candidates[0] if len(candidates) == 1 else None

    def ref_id(self, source: CompilerDeclarationName | None, ref: str, kinds: set[str] | None = None, standard: bool = False) -> str:
        item = self.resolve(source, ref, kinds)
        if item:
            return self.identity(item)["declarationId"]
        if standard:
            name = re.sub(r"[^A-Za-z0-9_-]", "_", _clean(ref).split(".")[-1].removesuffix("?")) or "Unknown"
            if name[0].isdigit():
                name = "_" + name
            return f"aidl.std.{name}@1"
        raise IrBuildError(f"unresolved IR reference '{_clean(ref)}'")


def _identity(resolver: _Resolver, item: CompilerDeclarationName) -> dict[str, Any]:
    return {**resolver.identity(item), "semanticHash": _ZERO_HASH}


def _take_type(tail: str) -> tuple[str, str]:
    tail = tail.strip()
    if tail.startswith("ref "):
        parts = tail.split(None, 2)
        return ("ref " + parts[1], parts[2] if len(parts) > 2 else "")
    stack: list[str] = []
    pairs = {")": "(", "]": "[", ">": "<"}
    for i, char in enumerate(tail):
        if char in "([<": stack.append(char)
        elif char in ")]>":
            if stack and stack[-1] == pairs[char]: stack.pop()
        elif char.isspace() and not stack:
            return tail[:i], tail[i + 1:].strip()
    return tail, ""


def _type(item: CompilerDeclarationName, resolver: _Resolver, raw: str, owners: Mapping[str, str]) -> dict[str, Any]:
    raw = raw.strip(); nullable = raw.endswith("?")
    if nullable: raw = raw[:-1]
    if raw.startswith("ref "):
        target = resolver.resolve(item, raw[4:], {"entity"})
        if not target: raise IrBuildError(f"unresolved entity ref '{raw[4:]}'")
        ident = resolver.identity(target); owner = owners.get(ident["fqn"])
        if not owner: raise IrBuildError(f"entity ref target '{ident['fqn']}' has no owner service")
        result: dict[str, Any] = {"kind": "ref", "entityId": ident["declarationId"], "entityFqn": ident["fqn"], "ownerServiceId": owner}
    elif raw.startswith("[") and raw.endswith("]"):
        result = {"kind": "list", "element": _type(item, resolver, raw[1:-1], owners)}
    elif raw.endswith(".id"):
        result = {"kind": "scalar", "name": "uuid"}
    else:
        scalar = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\((.*)\))?", raw, re.S)
        if scalar and scalar.group(1) in _SCALARS:
            result = {"kind": "scalar", "name": scalar.group(1)}
            constraints: dict[str, Any] = {}
            args = scalar.group(2) or ""
            rng = re.fullmatch(r"(\d+)\s*\.\.\s*(\d+)", args)
            if rng and scalar.group(1) == "string": constraints = {"minLength": int(rng.group(1)), "maxLength": int(rng.group(2))}
            for part in _split(args):
                if ":" in part and scalar.group(1) in {"int", "decimal"}:
                    key, value = [x.strip() for x in part.split(":", 1)]
                    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
                        number: int | float = float(value) if "." in value else int(value)
                        if key == "min": constraints["minimum"] = number
                        if key == "max": constraints["maximum"] = number
            if constraints: result["constraints"] = constraints
        else:
            generic = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.-]*)<(.*)>", raw, re.S)
            name = generic.group(1) if generic else raw
            target = resolver.resolve(item, name)
            if target:
                ident = resolver.identity(target); fqn = ident["fqn"]; decl_id = ident["declarationId"]
            else:
                safe = re.sub(r"[^A-Za-z0-9_-]", "_", name.split(".")[-1]) or "Unknown"
                fqn = f"aidl.std.{safe}"; decl_id = f"{fqn}@1"
            result = {"kind": "named", "declarationId": decl_id, "fqn": fqn, "typeArguments": []}
            if generic: result["typeArguments"] = [_type(item, resolver, arg, owners) for arg in _split(generic.group(2))]
    return {"kind": "nullable", "element": result} if nullable else result


def _field(item: CompilerDeclarationName, resolver: _Resolver, text: str, owners: Mapping[str, str]) -> dict[str, Any] | None:
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)$", text, re.S)
    if not match: return None
    name, tail = match.groups(); type_expr, mods = _take_type(tail)
    result = {"name": name, "type": _type(item, resolver, type_expr, owners), "required": not type_expr.endswith("?"), "mutable": bool(re.search(r"\bmutable\b", mods)), "sensitive": bool(re.search(r"\bsensitive\b", mods)), "generated": bool(re.search(r"\bgenerated\b", mods))}
    if re.search(r"\bprimary\b", mods): result["primary"] = True
    if re.search(r"\bconcurrencyToken\b", mods): result["concurrencyToken"] = True
    delete = re.search(r"\bonDelete\s+(restrict|cascade|setNull|none)\b", mods)
    if delete: result["onDelete"] = delete.group(1)
    return result


def _record(item: CompilerDeclarationName, resolver: _Resolver, owners: Mapping[str, str]) -> dict[str, Any]:
    raw = item.declaration.node.attrs.get("parameters")
    if not isinstance(raw, str): return {"kind": "record", "fields": []}
    raw = raw.strip()[1:-1] if raw.strip().startswith("(") and raw.strip().endswith(")") else raw
    fields = []
    for part in _split(raw):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)$", part, re.S)
        if not match: continue
        name, tail = match.groups(); type_expr, mods = _take_type(tail)
        fields.append({"name": name, "type": _type(item, resolver, type_expr, owners), "required": not type_expr.endswith("?") and "default" not in mods})
    return {"kind": "record", "fields": fields}


def _output(item: CompilerDeclarationName, resolver: _Resolver, owners: Mapping[str, str]) -> dict[str, Any]:
    raw = item.declaration.node.attrs.get("returns")
    return _type(item, resolver, raw.strip(), owners) if isinstance(raw, str) and raw.strip() else {"kind": "record", "fields": []}


def _expr(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw == "null": return {"kind": "literal", "value": None}
    if raw in {"true", "false"}: return {"kind": "literal", "value": raw == "true"}
    if re.fullmatch(r"-?\d+(?:\.\d+)?", raw): return {"kind": "literal", "value": float(raw) if "." in raw else int(raw)}
    if len(raw) > 1 and raw[0] == raw[-1] == '"': return {"kind": "literal", "value": _unquote(raw)}
    if raw.startswith("{") and raw.endswith("}"):
        return {"kind": "record", "fields": [{"name": key.strip(), "value": _expr(value)} for part in _split(raw[1:-1]) if ":" in part for key, value in [part.split(":", 1)]]}
    if raw in {"operationId()", "now()"}:
        return {"kind": "call", "function": raw[:-2], "arguments": []}
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", raw): return {"kind": "symbol", "path": raw.split(".")}
    return {"kind": "symbol", "path": [re.sub(r"\s+", " ", raw)]}


def _auth(item: CompilerDeclarationName) -> dict[str, Any]:
    mode = (_value(item.declaration.node, "auth") or "authenticated").split()[0]
    result: dict[str, Any] = {"mode": mode if mode in {"public", "authenticated", "service", "inherit"} else "authenticated"}
    if result["mode"] == "public":
        annotations = item.declaration.node.attrs.get("annotations")
        if isinstance(annotations, list):
            for ann in annotations:
                if isinstance(ann, Mapping) and ann.get("name") == "publicReason" and isinstance(ann.get("arguments"), str):
                    match = re.search(r'"([^"\n]+)"', ann["arguments"])
                    if match: result["publicReason"] = match.group(1)
    return result


def _ids(item: CompilerDeclarationName, resolver: _Resolver, value: str | None, kinds: set[str] | None = None, standard: bool = False) -> list[str]:
    return [resolver.ref_id(item, ref, kinds, standard) for ref in _list(value)]


def _read(item: CompilerDeclarationName, resolver: _Resolver) -> dict[str, Any]:
    path: str | None = None
    for index, child in enumerate(item.declaration.node.children):
        match = re.match(r"^read\s*:\s*(.*)$", _text(child), re.S)
        if match:
            parts = [match.group(1).strip()]
            for other in item.declaration.node.children[index + 1:]:
                if not _text(other).startswith("."): break
                parts.append(_text(other))
            path = "".join(parts); break
    if not path: raise IrBuildError(f"query '{item.declaration.name}' has no read path")
    root = re.match(r"^([A-Za-z_][A-Za-z0-9_.-]*)", path)
    if not root: raise IrBuildError(f"query '{item.declaration.name}' has invalid read path")
    steps = []
    for call in re.finditer(r"\.([A-Za-z_][A-Za-z0-9_]*)\(([^()]*)\)", re.sub(r"\s+", " ", path)):
        kind = "filter" if call.group(1) == "where" else call.group(1)
        if kind not in {"byId", "require", "filter", "sort", "page", "limit", "project"}: continue
        step: dict[str, Any] = {"kind": kind}; args = call.group(2).strip()
        if kind == "project" and args: step["projectionId"] = resolver.ref_id(item, args, {"view"}, True)
        elif args: step["arguments"] = [_expr(arg) for arg in _split(args)]
        steps.append(step)
    return {"entityId": resolver.ref_id(item, root.group(1), {"entity"}), "steps": steps}


def _idempotency(item: CompilerDeclarationName, scope: str) -> dict[str, Any] | None:
    block = _block(item.declaration.node, "idempotency")
    if block:
        key, scoped, retain = _value(block, "key"), _value(block, "scope"), _value(block, "retain")
        if key and retain: return {"key": _expr(key), "scope": _expr(scoped) if scoped else {"kind": "literal", "value": scope}, "retentionMs": _ms(retain)}
    inline = _value(item.declaration.node, "idempotency")
    if inline and (match := re.match(r"^(.*?)\s+retain\s+(\S+)$", inline, re.S)):
        return {"key": _expr(match.group(1)), "scope": {"kind": "literal", "value": scope}, "retentionMs": _ms(match.group(2))}
    return None


def _transaction_text(node: Node) -> str:
    text = re.sub(r"\s*\.\s*", ".", _text(node))
    text = re.sub(r"([A-Za-z0-9_)])\s+\(", r"\1(", text)
    return text


def _transaction(item: CompilerDeclarationName, resolver: _Resolver, block: Node) -> dict[str, Any]:
    match = re.match(r"^transaction\s+on\s+(\S+)(?:\s+isolation\s+(\w+))?", _text(block))
    if not match: raise IrBuildError(f"invalid transaction on '{item.declaration.name}'")
    steps: list[dict[str, Any]] = []; result = {"kind": "literal", "value": None}; vars: dict[str, str] = {}
    flat: list[Node] = []
    def flatten(children: list[Node]) -> None:
        for child in children:
            if child.kind == "blockClause" and (_text(child).startswith("when ") or _text(child) == "else"): flatten(child.children)
            else: flat.append(child)
    flatten(block.children)
    for child in flat:
        text = _transaction_text(child)
        if (ret := re.match(r"^return\s+(.+)$", text, re.S)): result = _expr(ret.group(1)); continue
        if (read := re.match(r"^(\w+)\s*=\s*([A-Za-z_][\w.-]*)\.(byId|require)\((.*?)\)(?:\s+else\s+(\S+))?", text, re.S)):
            bind, entity, method, args, error = read.groups(); vars[bind] = entity
            step: dict[str, Any] = {"kind": "read", "bind": bind, "read": {"entityId": resolver.ref_id(item, entity, {"entity"}), "steps": [{"kind": method, "arguments": [_expr(arg) for arg in _split(args)] if args else []}]}}
            if error: step["elseErrorId"] = resolver.ref_id(item, error, {"error"}, True)
            steps.append(step); continue
        if (create := re.match(r"^(\w+)\s*=\s*([A-Za-z_][\w.-]*)\.create\((.*)\)$", text, re.S)):
            bind, entity, args = create.groups(); vars[bind] = entity
            values = [{"field": key.strip(), "value": _expr(value)} for part in _split(args.strip("{}")) if ":" in part for key, value in [part.split(":", 1)]]
            steps.append({"kind": "write", "action": "create", "entityId": resolver.ref_id(item, entity, {"entity"}), "values": values}); continue
        if (write := re.match(r"^write\s*:\s*(\w+)\.(create|update|delete|upsert)\((.*)\)$", text, re.S)):
            target, action, args = write.groups(); entity = vars.get(target, target)
            values = [{"field": key.strip(), "value": _expr(value)} for part in _split(args) if ":" in part for key, value in [part.split(":", 1)]]
            step = {"kind": "write", "action": action, "entityId": resolver.ref_id(item, entity, {"entity"}), "values": values}
            if action != "create": step["target"] = {"kind": "symbol", "path": [target]}
            steps.append(step); continue
        if (emit := re.match(r"^emit\s*:\s*([A-Za-z_][\w.-]*)\((.*)\)\s+to\s+([A-Za-z_][\w.-]*)\s+via\s+outbox$", text, re.S)):
            event, args, topic = emit.groups(); payload = [{"name": key.strip(), "value": _expr(value)} for part in _split(args) if ":" in part for key, value in [part.split(":", 1)]]
            steps.append({"kind": "publish", "eventId": resolver.ref_id(item, event, {"event"}), "topicId": resolver.ref_id(item, topic, {"topic"}), "payload": {"kind": "record", "fields": payload}, "via": "outbox"})
    return {"kind": "transaction", "resourceId": resolver.ref_id(item, match.group(1), {"resource"}), "isolation": match.group(2) or "readCommitted", "steps": steps, "result": result}


def _root_effect(item: CompilerDeclarationName, resolver: _Resolver) -> dict[str, Any]:
    for child in item.declaration.node.children:
        if child.kind == "blockClause" and _text(child).startswith("transaction on "): return _transaction(item, resolver, child)
    start = _value(item.declaration.node, "start")
    if start and (match := re.match(r"^(workflow|saga|task)\s+([A-Za-z_][\w.-]*)\((.*)\)$", start, re.S)):
        return {"kind": "start", "targetKind": match.group(1), "targetId": resolver.ref_id(item, match.group(2), {match.group(1)}), "input": _expr(match.group(3))}
    raise IrBuildError(f"mutation '{item.declaration.name}' has no projectable root effect")


def _declaration(item: CompilerDeclarationName, resolver: _Resolver, owners: Mapping[str, str]) -> dict[str, Any]:
    kind = item.declaration.kind; result = _identity(resolver, item); result["kind"] = kind
    if kind == "enum": result["values"] = list(item.declaration.node.attrs.get("cases") or [])
    elif kind in {"alias", "opaque"}:
        raw = item.declaration.node.attrs.get("type")
        if not isinstance(raw, str): raise IrBuildError(f"{kind} '{item.declaration.name}' has no type")
        result["target" if kind == "alias" else "representation"] = _type(item, resolver, raw, owners)
    elif kind in {"value", "entity", "event"}:
        result["fields"] = [field for child in item.declaration.node.children if (field := _field(item, resolver, _text(child), owners))]
        if kind == "entity":
            result["identityFields"] = [field["name"] for field in result["fields"] if field.get("primary")] or [field["name"] for field in result["fields"] if field["name"] == "id"]
            if not result["identityFields"]: raise IrBuildError(f"entity '{item.declaration.name}' has no identity field")
        if kind == "event": result["majorVersion"] = _major(item)
    elif kind == "view":
        source = item.declaration.node.attrs.get("from")
        if not isinstance(source, str): raise IrBuildError(f"view '{item.declaration.name}' has no source")
        result.update({"sourceEntityId": resolver.ref_id(item, source, {"entity"}), "fields": []})
    elif kind == "error":
        result.update({"code": _unquote(_value(item.declaration.node, "code") or item.declaration.name or "ERROR"), "safeMessage": _unquote(_value(item.declaration.node, "safeMessage") or ""), "retry": _value(item.declaration.node, "retry") or "never", "transportStatus": int(_value(item.declaration.node, "httpStatus") or "500")})
    elif kind == "query":
        result.update({"input": _record(item, resolver, owners), "output": _output(item, resolver, owners), "auth": _auth(item), "errorIds": _ids(item, resolver, _value(item.declaration.node, "errors"), {"error"}, True), "read": _read(item, resolver), "consistency": _value(item.declaration.node, "consistency") or "strong"})
        if (allow := _value(item.declaration.node, "allow")): result["allow"] = _expr(allow)
        if (timeout := _value(item.declaration.node, "timeout")): result["timeoutMs"] = _ms(timeout)
    elif kind == "mutation":
        idem = _idempotency(item, "mutation"); allow = _value(item.declaration.node, "allow")
        if not idem or not allow: raise IrBuildError(f"mutation '{item.declaration.name}' lacks IR contract")
        result.update({"input": _record(item, resolver, owners), "output": _output(item, resolver, owners), "auth": _auth(item), "allow": _expr(allow), "errorIds": _ids(item, resolver, _value(item.declaration.node, "errors"), {"error"}, True), "idempotency": idem, "rootEffect": _root_effect(item, resolver)})
        if (timeout := _value(item.declaration.node, "timeout")): result["timeoutMs"] = _ms(timeout)
    elif kind in {"workflow", "saga", "task"}:
        result.update({"input": _record(item, resolver, owners), "output": _output(item, resolver, owners), "steps": []})
        if (idem := _idempotency(item, kind)): result["idempotency"] = idem
    elif kind == "api":
        ops = []
        for ref in _list(_value(item.declaration.node, "operations")):
            match = re.match(r"^(query|mutation)\s+(.+)$", ref, re.S)
            if match: ops.append({"kind": match.group(1), "operationId": resolver.ref_id(item, match.group(2), {match.group(1)})})
        result.update({"transport": _value(item.declaration.node, "transport") or "rest", "majorVersion": int(_value(item.declaration.node, "version") or "1"), "operations": ops, "auth": {"mode": (_value(item.declaration.node, "auth") or "inherit").split()[0]}, "errorEncoding": _value(item.declaration.node, "errors") or "problemDetails", "compatibility": _value(item.declaration.node, "compatibility") or "backward"})
        if (path := _value(item.declaration.node, "basePath")): result["basePath"] = _unquote(path)
        if (rate := _value(item.declaration.node, "rateLimit")) and (match := re.match(r"^(principal|ip|service)\s+(\d+)\s+per\s+(\S+)\s+burst\s+(\d+)$", rate)):
            result["rateLimit"] = {"key": match.group(1), "requests": int(match.group(2)), "windowMs": _ms(match.group(3)), "burst": int(match.group(4))}
    elif kind == "topic":
        partition = re.sub(r"^by\s+", "", _value(item.declaration.node, "partition") or "id")
        dead = re.search(r"after\s+(\d+)\s+attempt", _value(item.declaration.node, "deadLetter") or "")
        result.update({"eventIds": _ids(item, resolver, _value(item.declaration.node, "events"), {"event"}), "delivery": _value(item.declaration.node, "delivery") or "atLeastOnce", "partitionField": partition, "ordering": _value(item.declaration.node, "ordering") or "none", "retentionMs": _ms(_value(item.declaration.node, "retention") or "1d"), "compatibility": _value(item.declaration.node, "compatibility") or "backward", "deadLetterAttempts": int(dead.group(1)) if dead else 1})
    elif kind == "consumer":
        event, topic = item.declaration.node.attrs.get("on"), item.declaration.node.attrs.get("from")
        if not isinstance(event, str) or not isinstance(topic, str): raise IrBuildError(f"consumer '{item.declaration.name}' lacks binding")
        retry = _value(item.declaration.node, "retry"); retry_ir: dict[str, Any] = {"kind": "none"}
        if retry and (match := re.search(r"exponential\(.*?attempts\s*:\s*(\d+).*?\)", retry)):
            initial = re.search(r"initial\s*:\s*([^,\s)]+)", retry); maximum = re.search(r"maxDelay\s*:\s*([^,\s)]+)", retry)
            retry_ir = {"kind": "exponential", "attempts": int(match.group(1)), "initialDelayMs": _ms(initial.group(1) if initial else "1s"), "maxDelayMs": _ms(maximum.group(1) if maximum else "1s")}
        result.update({"eventId": resolver.ref_id(item, event, {"event"}), "topicId": resolver.ref_id(item, topic, {"topic"}), "retry": retry_ir, "effect": None})
        if (idem := _idempotency(item, "consumer")): result["idempotency"] = idem
        if (start := _value(item.declaration.node, "start")) and (match := re.match(r"^(workflow|saga|task)\s+([A-Za-z_][\w.-]*)\((.*)\)$", start, re.S)):
            result["effect"] = {"kind": "start", "targetKind": match.group(1), "targetId": resolver.ref_id(item, match.group(2), {match.group(1)}), "input": _expr(match.group(3))}
    return result


def _owners(resolver: _Resolver) -> dict[str, str]:
    owners: dict[str, str] = {}
    for service in resolver.project.declaration_names:
        if service.declaration.kind != "service": continue
        service_id = resolver.identity(service)["declarationId"]
        for ref in _list(_value(service.declaration.node, "owns")):
            entity = resolver.resolve(service, ref, {"entity"})
            if entity: owners[resolver.identity(entity)["fqn"]] = service_id
    return owners


def _service(item: CompilerDeclarationName, resolver: _Resolver) -> dict[str, Any]:
    result = _identity(resolver, item)
    result.update({"owns": _ids(item, resolver, _value(item.declaration.node, "owns"), {"entity"}), "uses": _ids(item, resolver, _value(item.declaration.node, "uses"), {"resource", "topic", "queue"}), "exposes": _ids(item, resolver, _value(item.declaration.node, "exposes"), {"query", "mutation"}), "runs": _ids(item, resolver, _value(item.declaration.node, "runs"), {"consumer", "workflow", "saga", "task"})})
    if (block := _block(item.declaration.node, "reliability")):
        rel = {}
        for source_key, target_key in [("idempotencyStore", "idempotencyStoreId"), ("inboxStore", "inboxStoreId"), ("workflowStore", "workflowStoreId")]:
            if (ref := _value(block, source_key)): rel[target_key] = resolver.ref_id(item, ref, {"resource"})
        if rel: result["reliability"] = rel
    return result


def _resource(item: CompilerDeclarationName, resolver: _Resolver) -> dict[str, Any]:
    result = _identity(resolver, item); kind = item.declaration.node.attrs.get("resourceKind")
    if not isinstance(kind, str): raise IrBuildError(f"resource '{item.declaration.name}' has no kind")
    result.update({"resourceKind": kind, "consistency": _value(item.declaration.node, "consistency") or "strong", "transactionIsolation": _list(_value(item.declaration.node, "transactions"))})
    if (migration := _value(item.declaration.node, "migrations")): result["migrationStrategy"] = migration
    if (backup := _value(item.declaration.node, "backup")) and (match := re.match(r"^rpo\s+(\S+)\s+rto\s+(\S+)$", backup)): result["backup"] = {"rpoMs": _ms(match.group(1)), "rtoMs": _ms(match.group(2))}
    if (encryption := _value(item.declaration.node, "encryption")): result["encryption"] = encryption
    return result


def _system(item: CompilerDeclarationName, resolver: _Resolver) -> tuple[dict[str, Any], list[CompilerDeclarationName], list[CompilerDeclarationName]]:
    services = []
    for ref in _list(_value(item.declaration.node, "services")):
        target = resolver.resolve(item, ref, {"service"})
        if not target: raise IrBuildError(f"unresolved system service '{ref}'")
        services.append(target)
    resources: list[CompilerDeclarationName] = []; topics = []
    for ref in _list(_value(item.declaration.node, "resources")):
        target = resolver.resolve(item, ref, {"resource", "topic"})
        if not target: raise IrBuildError(f"unresolved system resource/topic '{ref}'")
        if target.declaration.kind == "resource": resources.append(target)
        else: topics.append(resolver.identity(target)["declarationId"])
    result = _identity(resolver, item)
    result.update({"services": [_service(x, resolver) for x in services], "resources": [_resource(x, resolver) for x in resources], "topicIds": topics, "apiIds": _ids(item, resolver, _value(item.declaration.node, "apis"), {"api"}), "edges": [], "consumerGroups": []})
    return result, services, resources


def _app(item: CompilerDeclarationName, resolver: _Resolver) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    system, deployment = _value(item.declaration.node, "system"), _value(item.declaration.node, "defaultDeployment")
    if not system or not deployment: raise IrBuildError("app must declare system and defaultDeployment")
    result = _identity(resolver, item); api = _value(item.declaration.node, "api")
    result.update({"systemId": resolver.ref_id(item, system, {"system"}), "apiIds": [resolver.ref_id(item, api, {"api"})] if api else [], "defaultDeploymentId": resolver.ref_id(item, deployment, {"deployment"})})
    for declaration in item.document.declarations:
        if declaration.kind != "auth": continue
        provider, subject, service_ids = _value(declaration.node, "provider"), _value(declaration.node, "subject"), _value(declaration.node, "serviceIdentities")
        if provider and subject and service_ids:
            claim = re.search(r'claim\s+("[^"]+")', subject)
            result["auth"] = {"provider": provider.split()[0], "subjectClaim": _unquote(claim.group(1)) if claim else "sub", "roles": _list(_value(declaration.node, "roles")), "scopes": _list(_value(declaration.node, "scopes")), "serviceIdentities": service_ids.split()[0]}
        break
    profiles = []
    for child in item.declaration.node.children:
        if (match := re.match(r"^profile\s+([a-z][a-z0-9-]*)\s+version\s+([1-9]\d*)$", _text(child))): profiles.append({"id": match.group(1), "major": int(match.group(2))})
    return result, profiles or [{"id": "core", "major": 1}]


def _deployment(item: CompilerDeclarationName, resolver: _Resolver, services: list[CompilerDeclarationName]) -> dict[str, Any]:
    result = _identity(resolver, item); target = _value(item.declaration.node, "target") or "local"
    regions = [_unquote(re.sub(r"^primary\s+", "", value)) for value in _values(item.declaration.node, "region")]
    service_bindings = []
    explicit = [child for child in item.declaration.node.children if child.kind == "blockClause" and _text(child).startswith("service ")]
    if explicit:
        for child in explicit: service_bindings.append({"serviceId": resolver.ref_id(item, _text(child).split(None, 1)[1], {"service"}), "adapter": target})
    elif any("services all" in _text(child) for child in item.declaration.node.children):
        service_bindings = [{"serviceId": resolver.identity(service)["declarationId"], "adapter": target} for service in services]
    resource_bindings = []
    for value in _values(item.declaration.node, "bind"):
        parts = value.split(None, 2)
        if len(parts) >= 2:
            adapter = parts[1]
            if adapter == "from" and len(parts) == 3: adapter = (re.match(r"[A-Za-z_][\w.-]*", parts[2]) or re.match(r".*", "from")).group(0)
            resource_bindings.append({"resourceId": resolver.ref_id(item, parts[0], {"resource", "topic"}), "adapter": adapter})
    result.update({"environment": _value(item.declaration.node, "environment") or "local", "regions": regions, "serviceBindings": service_bindings, "resourceBindings": resource_bindings})
    return result


def _source_entry(path: str, item: CompilerDeclarationName, resolver: _Resolver) -> dict[str, Any]:
    span, end = item.declaration.span, item.declaration.end or item.declaration.span
    if not span or not end: raise IrBuildError(f"declaration '{item.declaration.name}' has no source span")
    return {"nodePath": path, "originalDeclarationId": resolver.identity(item)["declarationId"], "span": {"file": item.document.source_path.as_posix(), "startLine": span.line, "startColumn": span.column, "endLine": end.line, "endColumn": end.column}}


def build_canonical_ir(analysis: CompilerAnalysis) -> dict[str, Any]:
    """Build M3 canonical IR from validated compiler analysis."""
    if any(diag.severity.value == "error" for diag in analysis.diagnostics):
        raise IrBuildError("compiler diagnostics contain errors")
    resolver = _Resolver(analysis); project = analysis.project
    apps = [x for x in project.declaration_names if x.declaration.kind == "app"]
    systems = [x for x in project.declaration_names if x.declaration.kind == "system"]
    if len(apps) != 1: raise IrBuildError(f"canonical IR requires exactly one app declaration; found {len(apps)}")
    if len(systems) != 1: raise IrBuildError(f"canonical IR requires exactly one system declaration; found {len(systems)}")
    app, profiles = _app(apps[0], resolver); system, services, resources = _system(systems[0], resolver); owners = _owners(resolver)
    decl_sources = [x for x in project.declaration_names if x.declaration.kind in _DECL_KINDS]
    declarations = [_declaration(x, resolver, owners) for x in decl_sources]
    deployment_sources = [x for x in project.declaration_names if x.declaration.kind == "deployment"]
    deployments = [_deployment(x, resolver, services) for x in deployment_sources]
    entries = [_source_entry("/app", apps[0], resolver)]
    entries += [_source_entry(f"/declarations/{i}", x, resolver) for i, x in enumerate(decl_sources)]
    entries += [_source_entry("/system", systems[0], resolver)]
    entries += [_source_entry(f"/system/services/{i}", x, resolver) for i, x in enumerate(services)]
    entries += [_source_entry(f"/system/resources/{i}", x, resolver) for i, x in enumerate(resources)]
    entries += [_source_entry(f"/deployments/{i}", x, resolver) for i, x in enumerate(deployment_sources)]
    raw = {"irVersion": IR_VERSION, "semanticHash": _ZERO_HASH, "profiles": profiles, "app": app, "declarations": declarations, "system": system, "deployments": deployments, "sourceMap": {"entries": entries}, "profileExtensions": {}}
    return apply_semantic_hashes(prepare_canonical_ir(raw))
