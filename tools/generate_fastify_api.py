from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from tools import generate_typescript_domain as domain_generator


IR_VERSION = "0.3.0"
GENERATED_API_PATH = "generated/api.ts"
_DOMAIN_KINDS = {"enum", "alias", "opaque", "value", "entity", "view"}
_OPERATION_KINDS = {"query", "mutation"}
_TS_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


class FastifyApiGeneratorError(ValueError):
    pass


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise FastifyApiGeneratorError(f"{label} must be a non-empty string")
    return value


def _symbol(value: Any, label: str) -> str:
    text = _string(value, label)
    if not _TS_IDENTIFIER.fullmatch(text):
        raise FastifyApiGeneratorError(f"{label} '{text}' is not a valid TypeScript identifier")
    return text


def _domain_symbols(declarations: list[Mapping[str, Any]]) -> dict[str, str]:
    symbols: dict[str, str] = {}
    ids_by_symbol: dict[str, str] = {}
    for declaration in declarations:
        if declaration.get("kind") not in _DOMAIN_KINDS:
            continue
        declaration_id = _string(declaration.get("declarationId"), "domain declarationId")
        symbol = _symbol(declaration.get("name"), "domain declaration name")
        prior = ids_by_symbol.get(symbol)
        if prior is not None and prior != declaration_id:
            raise FastifyApiGeneratorError(
                f"domain declarations '{prior}' and '{declaration_id}' collide on TypeScript symbol '{symbol}'"
            )
        ids_by_symbol[symbol] = declaration_id
        symbols[declaration_id] = symbol
    return symbols


def _type_ref(type_ref: Any, symbols_by_id: Mapping[str, str]) -> str:
    try:
        return domain_generator._type_ref(type_ref, symbols_by_id)
    except domain_generator.TypeScriptDomainGeneratorError as exc:
        raise FastifyApiGeneratorError(str(exc)) from exc


def _base_path(api: Mapping[str, Any]) -> str:
    raw = api.get("basePath", "/")
    path = _string(raw, "api basePath")
    if not path.startswith("/"):
        raise FastifyApiGeneratorError(f"api basePath '{path}' must start with '/'")
    return path.rstrip("/") or ""


def _route_path(api: Mapping[str, Any], operation: Mapping[str, Any]) -> str:
    name = _string(operation.get("name"), "operation name")
    return f"{_base_path(api)}/{name}"


def _operation_method(kind: str) -> str:
    if kind == "query":
        return "GET"
    if kind == "mutation":
        return "POST"
    raise FastifyApiGeneratorError(f"unsupported API operation kind '{kind}'")


def generate_fastify_api(ir: Mapping[str, Any]) -> str:
    """Generate deterministic M4-03 Fastify REST contracts/routes from canonical IR only."""

    if ir.get("irVersion") != IR_VERSION:
        raise FastifyApiGeneratorError(f"unsupported canonical IR version '{ir.get('irVersion')}'")

    raw_declarations = ir.get("declarations")
    if not isinstance(raw_declarations, list):
        raise FastifyApiGeneratorError("canonical IR declarations must be an array")
    declarations: list[Mapping[str, Any]] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for declaration in raw_declarations:
        if not isinstance(declaration, Mapping):
            raise FastifyApiGeneratorError("canonical IR declaration must be an object")
        declarations.append(declaration)
        declaration_id = declaration.get("declarationId")
        if isinstance(declaration_id, str) and declaration_id:
            by_id[declaration_id] = declaration

    symbols_by_id = _domain_symbols(declarations)
    apis = [declaration for declaration in declarations if declaration.get("kind") == "api"]
    apis.sort(key=lambda declaration: (_string(declaration.get("fqn"), "api fqn"), _string(declaration.get("declarationId"), "api declarationId")))

    exposed: list[tuple[Mapping[str, Any], Mapping[str, Any], str, str]] = []
    operation_contracts: dict[str, Mapping[str, Any]] = {}
    operation_symbols: dict[str, str] = {}
    ids_by_symbol: dict[str, str] = {}
    route_keys: set[tuple[str, str]] = set()

    for api in apis:
        transport = _string(api.get("transport"), "api transport")
        if transport != "rest":
            raise FastifyApiGeneratorError(
                f"api '{api.get('fqn')}' uses unsupported transport '{transport}' for the Fastify REST generator"
            )
        operations = api.get("operations")
        if not isinstance(operations, list):
            raise FastifyApiGeneratorError("api operations must be an array")
        for mapping in operations:
            if not isinstance(mapping, Mapping):
                raise FastifyApiGeneratorError("api operation mapping must be an object")
            kind = _string(mapping.get("kind"), "api operation kind")
            if kind not in _OPERATION_KINDS:
                raise FastifyApiGeneratorError(f"unsupported API operation kind '{kind}'")
            operation_id = _string(mapping.get("operationId"), "api operationId")
            operation = by_id.get(operation_id)
            if operation is None:
                raise FastifyApiGeneratorError(f"api operation '{operation_id}' is not present in canonical IR declarations")
            if operation.get("kind") != kind:
                raise FastifyApiGeneratorError(
                    f"api operation '{operation_id}' kind '{kind}' does not match declaration kind '{operation.get('kind')}'"
                )
            symbol = _symbol(operation.get("name"), "operation name")
            prior = ids_by_symbol.get(symbol)
            if prior is not None and prior != operation_id:
                raise FastifyApiGeneratorError(
                    f"operations '{prior}' and '{operation_id}' collide on TypeScript symbol '{symbol}'"
                )
            ids_by_symbol[symbol] = operation_id
            operation_symbols[operation_id] = symbol
            operation_contracts[operation_id] = operation
            method = _operation_method(kind)
            path = _route_path(api, operation)
            route_key = (method, path)
            if route_key in route_keys:
                raise FastifyApiGeneratorError(f"duplicate generated route '{method} {path}'")
            route_keys.add(route_key)
            exposed.append((api, operation, method, path))

    exposed.sort(key=lambda item: (_string(item[0].get("fqn"), "api fqn"), item[3], item[2], _string(item[1].get("declarationId"), "operation declarationId")))

    imports = sorted(set(symbols_by_id.values()))
    blocks = [
        "// Generated from canonical AIDL IR by the M4 Fastify API generator.",
        "// M4-03 API contracts/routes only; persistence and later runtime behavior are intentionally absent.",
        'import type { FastifyInstance } from "fastify";',
    ]
    if imports:
        blocks.append(f'import type {{ {", ".join(imports)} }} from "./domain.js";')

    for operation_id in sorted(operation_contracts, key=lambda value: (_string(operation_contracts[value].get("fqn"), "operation fqn"), value)):
        operation = operation_contracts[operation_id]
        symbol = operation_symbols[operation_id]
        blocks.append(f"export type {symbol}Input = {_type_ref(operation.get('input'), symbols_by_id)};")
        blocks.append(f"export type {symbol}Output = {_type_ref(operation.get('output'), symbols_by_id)};")

    handler_lines = ["export interface ApiHandlers {"]
    for operation_id in sorted(operation_contracts, key=lambda value: (operation_symbols[value], value)):
        operation = operation_contracts[operation_id]
        symbol = operation_symbols[operation_id]
        name = _symbol(operation.get("name"), "operation name")
        handler_lines.append(
            f"  readonly {name}: (input: {symbol}Input) => Promise<{symbol}Output> | {symbol}Output;"
        )
    handler_lines.append("}")
    blocks.append("\n".join(handler_lines))

    route_contracts: list[dict[str, Any]] = []
    for api, operation, method, path in exposed:
        route_contracts.append(
            {
                "apiId": _string(api.get("declarationId"), "api declarationId"),
                "operationId": _string(operation.get("declarationId"), "operation declarationId"),
                "kind": _string(operation.get("kind"), "operation kind"),
                "method": method,
                "path": path,
                "authMode": (api.get("auth") or {}).get("mode") if isinstance(api.get("auth"), Mapping) else None,
                "errorIds": list(operation.get("errorIds") or []),
            }
        )
    contract_json = json.dumps(route_contracts, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    blocks.append(f"export const apiRoutes = {contract_json} as const;")

    route_lines = ["export function registerApiRoutes(app: FastifyInstance, handlers: ApiHandlers): void {"]
    for _api, operation, method, path in exposed:
        symbol = operation_symbols[_string(operation.get("declarationId"), "operation declarationId")]
        name = _symbol(operation.get("name"), "operation name")
        fastify_method = "get" if method == "GET" else "post"
        request_source = "request.query" if method == "GET" else "request.body"
        route_lines.extend(
            [
                f"  app.{fastify_method}({json.dumps(path)}, async (request, reply) => {{",
                f"    const result = await handlers.{name}({request_source} as {symbol}Input);",
                "    return reply.send(result);",
                "  });",
            ]
        )
    route_lines.append("}")
    blocks.append("\n".join(route_lines))

    return "\n\n".join(blocks) + "\n"


def generate_fastify_api_files(ir: Mapping[str, Any]) -> dict[str, str]:
    return {GENERATED_API_PATH: generate_fastify_api(ir)}
