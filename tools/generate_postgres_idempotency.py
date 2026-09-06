from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


IR_VERSION = "0.3.0"
GENERATED_IDEMPOTENCY_PATH = "generated/idempotency.ts"
GENERATED_MIGRATION_PATH = "generated/migrations/0002_idempotency.sql"


class PostgresIdempotencyGeneratorError(ValueError):
    pass


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PostgresIdempotencyGeneratorError(f"{label} must be a non-empty string")
    return value


def _ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _ts_symbol(value: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9_$]+", value) if part]
    symbol = "".join(part[:1].upper() + part[1:] for part in parts) or "Mutation"
    if symbol[0].isdigit():
        symbol = "_" + symbol
    return symbol


def _expr(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PostgresIdempotencyGeneratorError(f"{label} must be a canonical value expression")
    kind = value.get("kind")
    if kind == "literal":
        literal = value.get("value")
        if not isinstance(literal, (str, int, float, bool)) or isinstance(literal, bool) and False:
            pass
        if literal is None or isinstance(literal, (dict, list)):
            raise PostgresIdempotencyGeneratorError(f"{label} literal must be scalar")
        return value
    if kind == "symbol":
        path = value.get("path")
        if not isinstance(path, list) or not path or not all(isinstance(part, str) and part for part in path):
            raise PostgresIdempotencyGeneratorError(f"{label} symbol path is invalid")
        if path[0] != "input":
            raise PostgresIdempotencyGeneratorError(f"{label} symbol must be rooted at input for M4-06")
        return value
    raise PostgresIdempotencyGeneratorError(f"{label} kind '{kind}' is outside M4-06")


def _declarations(ir: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    raw = ir.get("declarations")
    if not isinstance(raw, list):
        raise PostgresIdempotencyGeneratorError("canonical IR declarations must be an array")
    declarations: list[Mapping[str, Any]] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for declaration in raw:
        if not isinstance(declaration, Mapping):
            raise PostgresIdempotencyGeneratorError("canonical IR declaration must be an object")
        declaration_id = declaration.get("declarationId")
        if isinstance(declaration_id, str) and declaration_id:
            by_id[declaration_id] = declaration
        declarations.append(declaration)
    return declarations, by_id


def _resources(ir: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    system = ir.get("system")
    if not isinstance(system, Mapping):
        raise PostgresIdempotencyGeneratorError("canonical IR system must be an object")
    raw = system.get("resources")
    if not isinstance(raw, list):
        raise PostgresIdempotencyGeneratorError("canonical IR system.resources must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for resource in raw:
        if not isinstance(resource, Mapping):
            raise PostgresIdempotencyGeneratorError("canonical IR resource must be an object")
        resource_id = _string(resource.get("declarationId"), "resource declarationId")
        result[resource_id] = resource
    return result


def _services(ir: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    system = ir.get("system")
    if not isinstance(system, Mapping):
        raise PostgresIdempotencyGeneratorError("canonical IR system must be an object")
    raw = system.get("services")
    if not isinstance(raw, list):
        raise PostgresIdempotencyGeneratorError("canonical IR system.services must be an array")
    services: list[Mapping[str, Any]] = []
    for service in raw:
        if not isinstance(service, Mapping):
            raise PostgresIdempotencyGeneratorError("canonical IR service must be an object")
        services.append(service)
    return services


def _mutation_service(mutation_id: str, services: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    owners: list[Mapping[str, Any]] = []
    for service in services:
        exposes = service.get("exposes")
        if isinstance(exposes, list) and mutation_id in exposes:
            owners.append(service)
    if len(owners) != 1:
        raise PostgresIdempotencyGeneratorError(
            f"mutation '{mutation_id}' must be exposed by exactly one service for M4-06; found {len(owners)}"
        )
    return owners[0]


def _plan_for_mutation(
    mutation: Mapping[str, Any],
    services: list[Mapping[str, Any]],
    resources: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    root = mutation.get("rootEffect")
    if not isinstance(root, Mapping) or root.get("kind") != "transaction":
        return None

    mutation_id = _string(mutation.get("declarationId"), "mutation declarationId")
    idem = mutation.get("idempotency")
    if not isinstance(idem, Mapping):
        raise PostgresIdempotencyGeneratorError(f"mutation '{mutation_id}' lacks canonical idempotency")
    retention = idem.get("retentionMs")
    if not isinstance(retention, int) or isinstance(retention, bool) or retention < 1:
        raise PostgresIdempotencyGeneratorError(f"mutation '{mutation_id}' has invalid idempotency retentionMs")
    key = _expr(idem.get("key"), f"mutation '{mutation_id}' idempotency key")
    scope = _expr(idem.get("scope"), f"mutation '{mutation_id}' idempotency scope")

    service = _mutation_service(mutation_id, services)
    reliability = service.get("reliability")
    if not isinstance(reliability, Mapping):
        raise PostgresIdempotencyGeneratorError(f"service for mutation '{mutation_id}' lacks reliability contract")
    store_id = _string(reliability.get("idempotencyStoreId"), "idempotencyStoreId")
    store = resources.get(store_id)
    if store is None:
        raise PostgresIdempotencyGeneratorError(f"idempotency store '{store_id}' is unresolved")
    if store.get("resourceKind") != "sql":
        raise PostgresIdempotencyGeneratorError(f"idempotency store '{store_id}' is not SQL")
    transaction_resource_id = _string(root.get("resourceId"), "transaction resourceId")
    if store_id != transaction_resource_id:
        raise PostgresIdempotencyGeneratorError(
            f"mutation '{mutation_id}' uses idempotency store '{store_id}' outside transaction resource '{transaction_resource_id}'; cross-resource idempotency is outside M4-06"
        )

    return {
        "operationId": mutation_id,
        "operationFqn": _string(mutation.get("fqn"), "mutation fqn"),
        "operationName": _string(mutation.get("name"), "mutation name"),
        "resourceId": store_id,
        "key": key,
        "scope": scope,
        "retentionMs": retention,
    }


def _migration_source() -> str:
    return '''-- Generated from canonical AIDL IR by the M4 PostgreSQL idempotency generator.\nCREATE TABLE IF NOT EXISTS "aidl_idempotency" (\n  "operation_id" text NOT NULL,\n  "scope" text NOT NULL,\n  "key" text NOT NULL,\n  "state" text NOT NULL,\n  "result" jsonb,\n  "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,\n  "expires_at" timestamptz NOT NULL,\n  PRIMARY KEY ("operation_id", "scope", "key"),\n  CONSTRAINT "ck_aidl_idempotency_state" CHECK ("state" IN ('running', 'completed'))\n);\n\nCREATE INDEX IF NOT EXISTS "ix_aidl_idempotency_expires_at" ON "aidl_idempotency" ("expires_at");\n'''


def _runtime_source(plans: list[dict[str, Any]]) -> str:
    plan_json = json.dumps(plans, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    existing_sql = _ts_string(
        'SELECT "state", "result" FROM "aidl_idempotency" WHERE "operation_id" = $1 AND "scope" = $2 AND "key" = $3 AND "expires_at" > CURRENT_TIMESTAMP'
    )
    claim_sql = _ts_string(
        'INSERT INTO "aidl_idempotency" ("operation_id", "scope", "key", "state", "expires_at") VALUES ($1, $2, $3, \'running\', CURRENT_TIMESTAMP + ($4 * INTERVAL \'1 millisecond\')) ON CONFLICT ("operation_id", "scope", "key") DO NOTHING RETURNING "operation_id"'
    )
    complete_sql = _ts_string(
        'UPDATE "aidl_idempotency" SET "state" = \'completed\', "result" = $4::jsonb WHERE "operation_id" = $1 AND "scope" = $2 AND "key" = $3'
    )
    cleanup_sql = _ts_string(
        'DELETE FROM "aidl_idempotency" WHERE "operation_id" = $1 AND "scope" = $2 AND "key" = $3 AND "state" = \'running\''
    )
    wrappers: list[str] = []
    used: set[str] = set()
    for index, plan in enumerate(plans):
        symbol = _ts_symbol(str(plan["operationName"]))
        if symbol in used:
            raise PostgresIdempotencyGeneratorError(f"TypeScript idempotency symbol collision for '{symbol}'")
        used.add(symbol)
        wrappers.append(
            f"export async function execute{symbol}Idempotent(client: PgIdempotencyClient, input: unknown, execute: () => Promise<unknown>): Promise<unknown> {{\n"
            f"  return executeIdempotentMutation(client, idempotencyPlans[{index}], input, execute);\n"
            f"}}"
        )
    wrapper_text = "\n\n".join(wrappers)
    return f'''// Generated from canonical AIDL IR. Do not edit by hand.\n\nexport interface PgIdempotencyResult {{ readonly rowCount: number | null; readonly rows: ReadonlyArray<Record<string, unknown>>; }}\nexport interface PgIdempotencyClient {{ query(sql: string, params?: ReadonlyArray<unknown>): Promise<PgIdempotencyResult>; }}\n\ntype Expr = Readonly<Record<string, unknown>>;\nexport interface IdempotencyPlan {{ readonly operationId: string; readonly operationFqn: string; readonly operationName: string; readonly resourceId: string; readonly key: Expr; readonly scope: Expr; readonly retentionMs: number; }}\n\nexport const idempotencyPlans: ReadonlyArray<IdempotencyPlan> = {plan_json} as ReadonlyArray<IdempotencyPlan>;\n\nfunction resolveExpr(expr: Expr, input: unknown): unknown {{\n  if (expr.kind === "literal") return expr.value;\n  if (expr.kind === "symbol") {{\n    const path = expr.path;\n    if (!Array.isArray(path) || path.length === 0 || path[0] !== "input") throw new Error("invalid canonical idempotency symbol expression");\n    let value: unknown = input;\n    for (const part of path.slice(1)) {{\n      if (value === null || typeof value !== "object") return undefined;\n      value = (value as Record<string, unknown>)[String(part)];\n    }}\n    return value;\n  }}\n  throw new Error(`unsupported canonical idempotency expression ${{String(expr.kind)}}`);\n}}\n\nfunction scalarKey(value: unknown, label: string): string {{\n  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);\n  throw new Error(`idempotency ${{label}} must resolve to a scalar`);\n}}\n\nexport async function executeIdempotentMutation(client: PgIdempotencyClient, plan: IdempotencyPlan, input: unknown, execute: () => Promise<unknown>): Promise<unknown> {{\n  const key = scalarKey(resolveExpr(plan.key, input), "key");\n  const scope = scalarKey(resolveExpr(plan.scope, input), "scope");\n  const existing = await client.query(\n    {existing_sql},\n    [plan.operationId, scope, key],\n  );\n  if ((existing.rowCount ?? 0) > 0) {{\n    const row = existing.rows[0];\n    if (row?.state === "completed") return row.result;\n    throw new Error("AIDL_IDEMPOTENCY_IN_PROGRESS");\n  }}\n  const claimed = await client.query(\n    {claim_sql},\n    [plan.operationId, scope, key, plan.retentionMs],\n  );\n  if ((claimed.rowCount ?? 0) !== 1) {{\n    const raced = await client.query(\n      {existing_sql},\n      [plan.operationId, scope, key],\n    );\n    if ((raced.rowCount ?? 0) > 0 && raced.rows[0]?.state === "completed") return raced.rows[0]?.result;\n    throw new Error("AIDL_IDEMPOTENCY_IN_PROGRESS");\n  }}\n  try {{\n    const result = await execute();\n    await client.query(\n      {complete_sql},\n      [plan.operationId, scope, key, JSON.stringify(result ?? null)],\n    );\n    return result;\n  }} catch (error) {{\n    await client.query({cleanup_sql}, [plan.operationId, scope, key]);\n    throw error;\n  }}\n}}\n\n{wrapper_text}\n'''


def generate_postgres_idempotency_files(ir: Mapping[str, Any]) -> dict[str, str]:
    """Generate deterministic M4-06 idempotency plumbing from canonical IR only."""
    if ir.get("irVersion") != IR_VERSION:
        raise PostgresIdempotencyGeneratorError(f"unsupported canonical IR version '{ir.get('irVersion')}'")
    declarations, _ = _declarations(ir)
    services = _services(ir)
    resources = _resources(ir)
    mutations = [declaration for declaration in declarations if declaration.get("kind") == "mutation"]
    mutations.sort(key=lambda declaration: (_string(declaration.get("fqn"), "mutation fqn"), _string(declaration.get("declarationId"), "mutation declarationId")))
    plans: list[dict[str, Any]] = []
    for mutation in mutations:
        plan = _plan_for_mutation(mutation, services, resources)
        if plan is not None:
            plans.append(plan)
    if not plans:
        raise PostgresIdempotencyGeneratorError("canonical IR contains no supported transaction mutations for M4-06")
    return {
        GENERATED_IDEMPOTENCY_PATH: _runtime_source(plans),
        GENERATED_MIGRATION_PATH: _migration_source(),
    }
