from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from tools.generate_postgres_outbox import PostgresOutboxGeneratorError, build_publish_step
from tools.generate_postgres_persistence import _table_name


IR_VERSION = "0.3.0"
GENERATED_TRANSACTIONS_PATH = "generated/transactions.ts"
_ISOLATION_SQL = {
    "readCommitted": "READ COMMITTED",
    "repeatableRead": "REPEATABLE READ",
    "serializable": "SERIALIZABLE",
}


class PostgresTransactionGeneratorError(ValueError):
    pass


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PostgresTransactionGeneratorError(f"{label} must be a non-empty string")
    return value


def _ts_symbol(value: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9_$]+", value) if part]
    symbol = "".join(part[:1].upper() + part[1:] for part in parts) or "Transaction"
    if symbol[0].isdigit():
        symbol = "_" + symbol
    return symbol


def _declarations(ir: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    raw = ir.get("declarations")
    if not isinstance(raw, list):
        raise PostgresTransactionGeneratorError("canonical IR declarations must be an array")
    declarations: list[Mapping[str, Any]] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for declaration in raw:
        if not isinstance(declaration, Mapping):
            raise PostgresTransactionGeneratorError("canonical IR declaration must be an object")
        declaration_id = declaration.get("declarationId")
        if isinstance(declaration_id, str) and declaration_id:
            by_id[declaration_id] = declaration
        declarations.append(declaration)
    return declarations, by_id


def _resources(ir: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    system = ir.get("system")
    if not isinstance(system, Mapping):
        raise PostgresTransactionGeneratorError("canonical IR system must be an object")
    raw = system.get("resources")
    if not isinstance(raw, list):
        raise PostgresTransactionGeneratorError("canonical IR system.resources must be an array")
    resources: dict[str, Mapping[str, Any]] = {}
    for resource in raw:
        if not isinstance(resource, Mapping):
            raise PostgresTransactionGeneratorError("canonical IR resource must be an object")
        resource_id = _string(resource.get("declarationId"), "resource declarationId")
        resources[resource_id] = resource
    return resources


def _entity_info(entity_id: str, declarations: Mapping[str, Mapping[str, Any]]) -> tuple[Mapping[str, Any], str, str | None]:
    entity = declarations.get(entity_id)
    if entity is None or entity.get("kind") != "entity":
        raise PostgresTransactionGeneratorError(f"transaction entity '{entity_id}' is unresolved")
    identities = entity.get("identityFields")
    fields = entity.get("fields")
    if not isinstance(identities, list) or len(identities) != 1 or not isinstance(identities[0], str):
        raise PostgresTransactionGeneratorError(f"entity '{entity_id}' requires exactly one identity field for M4-05")
    if not isinstance(fields, list):
        raise PostgresTransactionGeneratorError(f"entity '{entity_id}' fields must be an array")
    tokens = [field.get("name") for field in fields if isinstance(field, Mapping) and field.get("concurrencyToken") is True]
    if len(tokens) > 1:
        raise PostgresTransactionGeneratorError(f"entity '{entity_id}' has multiple concurrency tokens")
    token = tokens[0] if tokens else None
    if token is not None and not isinstance(token, str):
        raise PostgresTransactionGeneratorError(f"entity '{entity_id}' has invalid concurrency token")
    return entity, identities[0], token


def _expr(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not isinstance(value.get("kind"), str):
        raise PostgresTransactionGeneratorError(f"{label} must be a canonical value expression")
    return value


def _quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _read_step(step: Mapping[str, Any], declarations: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    bind = _string(step.get("bind"), "transaction read bind")
    read = step.get("read")
    if not isinstance(read, Mapping):
        raise PostgresTransactionGeneratorError(f"transaction read '{bind}' must contain read plan")
    entity_id = _string(read.get("entityId"), "transaction read entityId")
    entity, identity, _ = _entity_info(entity_id, declarations)
    steps = read.get("steps")
    if not isinstance(steps, list) or len(steps) != 1 or not isinstance(steps[0], Mapping):
        raise PostgresTransactionGeneratorError(f"transaction read '{bind}' supports exactly one byId/require step")
    read_kind = steps[0].get("kind")
    if read_kind not in {"byId", "require"}:
        raise PostgresTransactionGeneratorError(f"transaction read '{bind}' kind '{read_kind}' is outside M4-05")
    arguments = steps[0].get("arguments")
    if not isinstance(arguments, list) or len(arguments) != 1:
        raise PostgresTransactionGeneratorError(f"transaction read '{bind}' requires one identity argument")
    argument = _expr(arguments[0], f"transaction read '{bind}' argument")
    result: dict[str, Any] = {
        "kind": "read",
        "bind": bind,
        "required": read_kind == "require",
        "sql": f"SELECT * FROM {_quoted(_table_name(entity))} WHERE {_quoted(identity)} = $1",
        "arguments": [argument],
    }
    if "elseErrorId" in step:
        result["elseErrorId"] = _string(step.get("elseErrorId"), "transaction read elseErrorId")
    if result["required"] and "elseErrorId" not in result:
        raise PostgresTransactionGeneratorError(f"required transaction read '{bind}' must declare elseErrorId")
    return result


def _write_values(step: Mapping[str, Any]) -> tuple[list[str], list[Mapping[str, Any]]]:
    raw = step.get("values")
    if not isinstance(raw, list):
        raise PostgresTransactionGeneratorError("transaction write values must be an array")
    fields: list[str] = []
    values: list[Mapping[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise PostgresTransactionGeneratorError("transaction write value must be an object")
        field = _string(item.get("field"), "transaction write field")
        if field in fields:
            raise PostgresTransactionGeneratorError(f"transaction write has duplicate field '{field}'")
        fields.append(field)
        values.append(_expr(item.get("value"), f"transaction write value '{field}'"))
    return fields, values


def _target_bind(step: Mapping[str, Any]) -> str:
    target = step.get("target")
    if not isinstance(target, Mapping) or target.get("kind") != "symbol":
        raise PostgresTransactionGeneratorError("transaction update/delete target must be a symbol binding")
    path = target.get("path")
    if not isinstance(path, list) or len(path) != 1 or not isinstance(path[0], str) or not path[0]:
        raise PostgresTransactionGeneratorError("transaction update/delete target must be a single binding symbol")
    return path[0]


def _write_step(
    step: Mapping[str, Any],
    declarations: Mapping[str, Mapping[str, Any]],
    create_bind: str | None = None,
) -> dict[str, Any]:
    action = step.get("action")
    if action not in {"create", "update", "delete"}:
        raise PostgresTransactionGeneratorError(f"transaction write action '{action}' is outside M4-05")
    entity_id = _string(step.get("entityId"), "transaction write entityId")
    entity, identity, token = _entity_info(entity_id, declarations)
    table = _quoted(_table_name(entity))
    fields, values = _write_values(step)

    if token is not None and token in fields:
        raise PostgresTransactionGeneratorError(f"transaction {action} must not assign concurrency token '{token}' directly")

    if action == "create":
        if "expectedRevision" in step:
            raise PostgresTransactionGeneratorError("create write cannot declare expectedRevision")
        if fields:
            columns = ", ".join(_quoted(field) for field in fields)
            params = ", ".join(f"${index}" for index in range(1, len(fields) + 1))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({params}) RETURNING *"
        else:
            sql = f"INSERT INTO {table} DEFAULT VALUES RETURNING *"
        result: dict[str, Any] = {"kind": "create", "sql": sql, "values": values}
        if create_bind is not None:
            result["bind"] = create_bind
        return result

    bind = _target_bind(step)
    if token is None:
        raise PostgresTransactionGeneratorError(f"entity '{entity_id}' needs a concurrencyToken for {action}")
    expected = step.get("expectedRevision")
    if expected is None:
        raise PostgresTransactionGeneratorError(f"transaction {action} on '{entity_id}' requires expectedRevision")
    expected_expr = _expr(expected, f"transaction {action} expectedRevision")
    else_error = _string(step.get("elseErrorId"), f"transaction {action} elseErrorId")

    if action == "update":
        assignments = [f"{_quoted(field)} = ${index}" for index, field in enumerate(fields, start=1)]
        assignments.append(f"{_quoted(token)} = {_quoted(token)} + 1")
        identity_param = len(values) + 1
        revision_param = len(values) + 2
        sql = (
            f"UPDATE {table} SET {', '.join(assignments)} "
            f"WHERE {_quoted(identity)} = ${identity_param} AND {_quoted(token)} = ${revision_param} RETURNING *"
        )
    else:
        sql = (
            f"DELETE FROM {table} WHERE {_quoted(identity)} = $1 "
            f"AND {_quoted(token)} = $2 RETURNING *"
        )
    return {
        "kind": action,
        "targetBind": bind,
        "identityField": identity,
        "concurrencyField": token,
        "sql": sql,
        "values": values,
        "expectedRevision": expected_expr,
        "elseErrorId": else_error,
    }


def _expression_roots(value: Any) -> list[str]:
    if not isinstance(value, Mapping):
        return []
    kind = value.get("kind")
    if kind == "symbol":
        path = value.get("path")
        if not isinstance(path, list) or not path or not isinstance(path[0], str):
            return []
        head = path[0]
        if head == "input" or head in {"operationId()", "now()"}:
            return []
        if len(path) == 1 and "(" in head:
            match = re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\((.*)\)", head)
            if not match:
                return []
            roots: list[str] = []
            for name in re.findall(r"\b([a-z_][A-Za-z0-9_]*)\b", match.group(1)):
                if name not in {"input", "operationId", "now"} and name not in roots:
                    roots.append(name)
            return roots
        return [head]
    if kind == "record":
        roots: list[str] = []
        fields = value.get("fields")
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, Mapping):
                    for root in _expression_roots(field.get("value")):
                        if root not in roots:
                            roots.append(root)
        return roots
    if kind == "call":
        roots: list[str] = []
        arguments = value.get("arguments")
        if isinstance(arguments, list):
            for argument in arguments:
                for root in _expression_roots(argument):
                    if root not in roots:
                        roots.append(root)
        return roots
    if kind == "list":
        roots: list[str] = []
        items = value.get("items")
        if isinstance(items, list):
            for item in items:
                for root in _expression_roots(item):
                    if root not in roots:
                        roots.append(root)
        return roots
    return []


def _recover_create_bindings(raw_steps: list[Any], result: Any) -> dict[int, str]:
    create_indexes = [
        index for index, step in enumerate(raw_steps)
        if isinstance(step, Mapping) and step.get("kind") == "write" and step.get("action") == "create"
    ]
    if not create_indexes:
        return {}
    known = {
        str(step.get("bind")) for step in raw_steps
        if isinstance(step, Mapping) and step.get("kind") == "read" and isinstance(step.get("bind"), str)
    }
    candidates: list[str] = []
    for step in raw_steps:
        if isinstance(step, Mapping) and step.get("kind") == "publish":
            for root in _expression_roots(step.get("payload")):
                if root not in known and root not in candidates:
                    candidates.append(root)
    for root in _expression_roots(result):
        if root not in known and root not in candidates:
            candidates.append(root)
    if not candidates:
        return {}
    if len(candidates) != len(create_indexes):
        raise PostgresTransactionGeneratorError(
            "canonical IR create-result binding recovery is ambiguous for M4-07"
        )
    return dict(zip(create_indexes, candidates, strict=True))


def _transaction_plan(
    mutation: Mapping[str, Any],
    declarations: Mapping[str, Mapping[str, Any]],
    resources: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    root = mutation.get("rootEffect")
    if not isinstance(root, Mapping) or root.get("kind") != "transaction":
        return None
    resource_id = _string(root.get("resourceId"), "transaction resourceId")
    resource = resources.get(resource_id)
    if resource is None:
        raise PostgresTransactionGeneratorError(f"transaction resource '{resource_id}' is unresolved")
    if resource.get("resourceKind") != "sql":
        raise PostgresTransactionGeneratorError(f"transaction resource '{resource_id}' is not SQL")
    isolation = _string(root.get("isolation"), "transaction isolation")
    isolation_sql = _ISOLATION_SQL.get(isolation)
    if isolation_sql is None:
        raise PostgresTransactionGeneratorError(f"unsupported PostgreSQL isolation '{isolation}'")
    supported = resource.get("transactionIsolation")
    if not isinstance(supported, list) or isolation not in supported:
        raise PostgresTransactionGeneratorError(
            f"resource '{resource_id}' does not declare transaction isolation '{isolation}'"
        )
    raw_steps = root.get("steps")
    if not isinstance(raw_steps, list):
        raise PostgresTransactionGeneratorError("transaction steps must be an array")
    result = _expr(root.get("result"), "transaction result")
    create_bindings = _recover_create_bindings(raw_steps, result)
    steps: list[dict[str, Any]] = []
    for index, step in enumerate(raw_steps):
        if not isinstance(step, Mapping):
            raise PostgresTransactionGeneratorError("transaction step must be an object")
        if step.get("kind") == "read":
            steps.append(_read_step(step, declarations))
        elif step.get("kind") == "write":
            steps.append(_write_step(step, declarations, create_bindings.get(index)))
        elif step.get("kind") == "publish":
            try:
                steps.append(build_publish_step(step, declarations))
            except PostgresOutboxGeneratorError as exc:
                raise PostgresTransactionGeneratorError(str(exc)) from exc
        else:
            raise PostgresTransactionGeneratorError(f"transaction step kind '{step.get('kind')}' is outside M4-05/M4-07")
    return {
        "operationId": _string(mutation.get("declarationId"), "mutation declarationId"),
        "operationFqn": _string(mutation.get("fqn"), "mutation fqn"),
        "operationName": _string(mutation.get("name"), "mutation name"),
        "resourceId": resource_id,
        "isolation": isolation,
        "isolationSql": isolation_sql,
        "steps": steps,
        "result": result,
    }


def _runtime_source(plans: list[dict[str, Any]]) -> str:
    plan_json = json.dumps(plans, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    wrappers: list[str] = []
    used: set[str] = set()
    for index, plan in enumerate(plans):
        symbol = _ts_symbol(str(plan["operationName"]))
        if symbol in used:
            raise PostgresTransactionGeneratorError(f"TypeScript transaction symbol collision for '{symbol}'")
        used.add(symbol)
        wrappers.append(
            f"export async function execute{symbol}Transaction(client: PgTransactionClient, input: unknown): Promise<unknown> {{\n"
            f"  return executeTransactionPlan(client, transactionPlans[{index}], input);\n"
            f"}}"
        )
    wrapper_text = "\n\n".join(wrappers)
    return f'''// Generated from canonical AIDL IR. Do not edit by hand.\n\nexport interface PgQueryResult {{ readonly rowCount: number | null; readonly rows: ReadonlyArray<Record<string, unknown>>; }}\nexport interface PgTransactionClient {{ query(sql: string, params?: ReadonlyArray<unknown>): Promise<PgQueryResult>; }}\n\nexport class AidlTransactionError extends Error {{\n  constructor(readonly errorId: string) {{ super(errorId); this.name = "AidlTransactionError"; }}\n}}\n\ntype Expr = Readonly<Record<string, unknown>>;\ntype Step = Readonly<Record<string, unknown>>;\nexport interface TransactionPlan {{ readonly operationId: string; readonly operationFqn: string; readonly operationName: string; readonly resourceId: string; readonly isolation: string; readonly isolationSql: string; readonly steps: ReadonlyArray<Step>; readonly result: Expr; }}\n\nexport const transactionPlans: ReadonlyArray<TransactionPlan> = {plan_json} as ReadonlyArray<TransactionPlan>;\n\nfunction resolveExpr(expr: Expr, input: unknown, bindings: Record<string, unknown>, transactionNow: string): unknown {{\n  if (expr.kind === "literal") return expr.value;\n  if (expr.kind === "symbol") {{\n    const path = expr.path;\n    if (!Array.isArray(path) || path.length === 0) throw new Error("invalid canonical symbol expression");\n    if (path.length === 1 && path[0] === "operationId()") {{\n      if (input === null || typeof input !== "object") throw new Error("operationId() requires mutation input");\n      const value = (input as Record<string, unknown>).operationId;\n      if (typeof value !== "string" && typeof value !== "number") throw new Error("operationId() requires input.operationId");\n      return value;\n    }}\n    if (path.length === 1 && path[0] === "now()") return transactionNow;\n    if (path.length === 1 && String(path[0]).includes("(")) throw new Error(`unsupported canonical producer symbol ${{String(path[0])}}`);\n    let value: unknown = path[0] === "input" ? input : bindings[String(path[0])];\n    for (const part of path.slice(1)) {{\n      if (value === null || typeof value !== "object") return undefined;\n      value = (value as Record<string, unknown>)[String(part)];\n    }}\n    return value;\n  }}\n  if (expr.kind === "call") {{\n    const fn = String(expr.function);\n    const args = expr.arguments;\n    if (!Array.isArray(args) || args.length !== 0) throw new Error(`unsupported canonical call ${{fn}}`);\n    if (fn === "operationId") {{\n      if (input === null || typeof input !== "object") throw new Error("operationId() requires mutation input");\n      const value = (input as Record<string, unknown>).operationId;\n      if (typeof value !== "string" && typeof value !== "number") throw new Error("operationId() requires input.operationId");\n      return value;\n    }}\n    if (fn === "now") return transactionNow;\n    throw new Error(`unsupported canonical call ${{fn}}`);\n  }}\n  if (expr.kind === "record") {{\n    const result: Record<string, unknown> = {{}};\n    const fields = expr.fields;\n    if (!Array.isArray(fields)) throw new Error("invalid canonical record expression");\n    for (const field of fields as ReadonlyArray<Record<string, unknown>>) result[String(field.name)] = resolveExpr(field.value as Expr, input, bindings, transactionNow);\n    return result;\n  }}\n  throw new Error(`unsupported canonical value expression ${{String(expr.kind)}}`);\n}}\n\nfunction requiredOutboxScalar(payload: Record<string, unknown>, field: string): string {{\n  const value = payload[field];\n  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);\n  throw new Error(`transactional outbox field ${{field}} must resolve to a scalar`);\n}}\n\nexport async function executeTransactionPlan(client: PgTransactionClient, plan: TransactionPlan, input: unknown): Promise<unknown> {{\n  const bindings: Record<string, unknown> = {{}};\n  const transactionNow = new Date().toISOString();\n  await client.query("BEGIN");\n  try {{\n    await client.query(`SET TRANSACTION ISOLATION LEVEL ${{plan.isolationSql}}`);\n    for (const step of plan.steps) {{\n      const kind = String(step.kind);\n      if (kind === "read") {{\n        const args = (step.arguments as ReadonlyArray<Expr>).map(expr => resolveExpr(expr, input, bindings, transactionNow));\n        const result = await client.query(String(step.sql), args);\n        const row = result.rows[0] ?? null;\n        if (step.required === true && row === null) throw new AidlTransactionError(String(step.elseErrorId));\n        bindings[String(step.bind)] = row;\n        continue;\n      }}\n      if (kind === "create") {{\n        const params = (step.values as ReadonlyArray<Expr>).map(expr => resolveExpr(expr, input, bindings, transactionNow));\n        const result = await client.query(String(step.sql), params);\n        if (step.bind !== undefined) {{\n          const row = result.rows[0] ?? null;\n          if (row === null) throw new Error(`create did not return binding ${{String(step.bind)}}`);\n          bindings[String(step.bind)] = row;\n        }}\n        continue;\n      }}\n      if (kind === "update" || kind === "delete") {{\n        const target = bindings[String(step.targetBind)] as Record<string, unknown> | null | undefined;\n        if (!target) throw new Error(`missing transaction binding ${{String(step.targetBind)}}`);\n        const params = kind === "update"\n          ? (step.values as ReadonlyArray<Expr>).map(expr => resolveExpr(expr, input, bindings, transactionNow))\n          : [];\n        params.push(target[String(step.identityField)]);\n        params.push(resolveExpr(step.expectedRevision as Expr, input, bindings, transactionNow));\n        const result = await client.query(String(step.sql), params);\n        if (result.rowCount !== 1) throw new AidlTransactionError(String(step.elseErrorId));\n        if (result.rows[0]) bindings[String(step.targetBind)] = result.rows[0];\n        continue;\n      }}\n      if (kind === "publish") {{\n        const resolved = resolveExpr(step.payload as Expr, input, bindings, transactionNow);\n        if (resolved === null || typeof resolved !== "object" || Array.isArray(resolved)) throw new Error("transactional outbox payload must resolve to a record");\n        const payload = resolved as Record<string, unknown>;\n        const eventId = requiredOutboxScalar(payload, "eventId");\n        const partitionKey = requiredOutboxScalar(payload, String(step.partitionField));\n        const occurredAt = payload.occurredAt;\n        if (typeof occurredAt !== "string") throw new Error("transactional outbox occurredAt must resolve to a datetime string");\n        await client.query(String(step.sql), [\n          eventId, String(step.eventFqn), Number(step.eventVersion), String(step.topicFqn), partitionKey,\n          JSON.stringify(payload), occurredAt, Number(step.retentionMs),\n        ]);\n        continue;\n      }}\n      throw new Error(`unsupported generated transaction step ${{kind}}`);\n    }}\n    const result = resolveExpr(plan.result, input, bindings, transactionNow);\n    await client.query("COMMIT");\n    return result;\n  }} catch (error) {{\n    await client.query("ROLLBACK");\n    throw error;\n  }}\n}}\n\n{wrapper_text}\n'''


def generate_postgres_transactions(ir: Mapping[str, Any]) -> str:
    """Generate deterministic M4-05/M4-07 transaction/concurrency runtime from canonical IR only."""
    if ir.get("irVersion") != IR_VERSION:
        raise PostgresTransactionGeneratorError(f"unsupported canonical IR version '{ir.get('irVersion')}'")
    declarations, by_id = _declarations(ir)
    resources = _resources(ir)
    mutations = [item for item in declarations if item.get("kind") == "mutation"]
    mutations.sort(key=lambda item: (_string(item.get("fqn"), "mutation fqn"), _string(item.get("declarationId"), "mutation declarationId")))
    plans = [plan for mutation in mutations if (plan := _transaction_plan(mutation, by_id, resources)) is not None]
    if not plans:
        raise PostgresTransactionGeneratorError("canonical IR contains no supported transaction mutations")
    return _runtime_source(plans)


def generate_postgres_transaction_files(ir: Mapping[str, Any]) -> dict[str, str]:
    return {GENERATED_TRANSACTIONS_PATH: generate_postgres_transactions(ir)}
